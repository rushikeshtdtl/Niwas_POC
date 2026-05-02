from collections import Counter
from datetime import datetime, timezone
from io import BytesIO
from statistics import pstdev

import cv2
import fitz
import numpy as np
from PIL import Image

from kyc_engine.config import get_rules
from kyc_engine.core.file_validator import FilePayload
from kyc_engine.models.schema import (
    AuditEntry,
    DocumentForensicsResult,
    ForensicLayerResult,
    ForensicsResult,
)


class ImageForensicsEngine:
    ANALYZED_DOCUMENTS = {
        "pan_file": "pan",
        "aadhaar_file": "aadhaar",
        "bank_statement": "statement",
    }

    def analyze(
        self,
        files: dict[str, FilePayload],
        audit_trail: list[AuditEntry],
    ) -> ForensicsResult:
        documents: list[DocumentForensicsResult] = []
        for field_name, document_type in self.ANALYZED_DOCUMENTS.items():
            result = self._analyze_document(document_type, files[field_name], audit_trail)
            documents.append(result)

        total_suspicious_layers = sum(len(document.suspicious_layers) for document in documents)
        high_risk_documents = [
            document.document_type for document in documents if len(document.suspicious_layers) >= 3
        ]
        fraud_signals: list[str] = []
        if high_risk_documents:
            fraud_signals.append("document_tampering_suspected")
        elif total_suspicious_layers >= 3:
            fraud_signals.append("document_forensics_review")

        audit_trail.append(
            AuditEntry(
                level="INFO",
                stage="FORENSICS",
                message=(
                    f"Forensics summary: total suspicious layers = {total_suspicious_layers}; "
                    f"high risk documents = {high_risk_documents or ['none']}; "
                    f"signals = {fraud_signals or ['none']}"
                ),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

        return ForensicsResult(
            documents=documents,
            total_suspicious_layers=total_suspicious_layers,
            high_risk_documents=high_risk_documents,
            fraud_signals=fraud_signals,
        )

    def _analyze_document(
        self,
        document_type: str,
        payload: FilePayload,
        audit_trail: list[AuditEntry],
    ) -> DocumentForensicsResult:
        image, metadata_text = self._load_image_and_metadata(payload)
        layers = [
            self._metadata_audit(metadata_text),
            self._error_level_analysis(image),
            self._fft_moire_detection(image),
            self._ai_artifact_detection(image),
            self._template_profile_check(document_type, image),
            self._text_density_check(document_type, image),
            self._text_alignment_check(image),
        ]
        suspicious_layers = [layer.layer_name for layer in layers if layer.suspicious]
        overall_score = min(100, int(round(sum(layer.score for layer in layers if layer.suspicious))))

        for layer in layers:
            level = "WARNING" if layer.suspicious else "INFO"
            audit_trail.append(
                AuditEntry(
                    level=level,
                    stage="FORENSICS",
                    message=(
                        f"{document_type}:{layer.layer_name} suspicious={layer.suspicious} "
                        f"score={layer.score:.2f} detail={layer.detail}"
                    ),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )

        return DocumentForensicsResult(
            document_type=document_type,
            overall_score=overall_score,
            suspicious_layers=suspicious_layers,
            layers=layers,
        )

    def _load_image_and_metadata(self, payload: FilePayload) -> tuple[Image.Image, str]:
        metadata_parts = [payload.filename, payload.content_type]
        if payload.extension == ".pdf":
            document = fitz.open(stream=payload.data, filetype="pdf")
            metadata = document.metadata or {}
            metadata_parts.extend(str(value) for value in metadata.values() if value)
            page = document.load_page(0)
            pixmap = page.get_pixmap(dpi=200)
            image = Image.open(BytesIO(pixmap.tobytes("png"))).convert("RGB")
            document.close()
            return image, " ".join(metadata_parts).lower()

        image = Image.open(BytesIO(payload.data)).convert("RGB")
        metadata_parts.extend(str(value) for value in image.info.values() if value)
        exif = image.getexif()
        if exif:
            metadata_parts.extend(str(value) for value in exif.values() if value)
        return image, " ".join(metadata_parts).lower()

    def _metadata_audit(self, metadata_text: str) -> ForensicLayerResult:
        rules = get_rules()
        markers = rules.forensics["editor_markers"]
        hits = [marker for marker in markers if marker in metadata_text]
        suspicious = bool(hits)
        return ForensicLayerResult(
            layer_name="metadata_audit",
            suspicious=suspicious,
            score=35.0 if suspicious else 0.0,
            detail="editor markers=" + (", ".join(hits) if hits else "none"),
        )

    def _error_level_analysis(self, image: Image.Image) -> ForensicLayerResult:
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=90)
        recompressed = Image.open(BytesIO(buffer.getvalue())).convert("RGB")
        diff = cv2.absdiff(np.array(image), np.array(recompressed))
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_RGB2GRAY)
        mean_diff = float(np.mean(diff_gray))
        hotspot_ratio = float(np.mean(diff_gray > 25))
        suspicious = mean_diff > 6.5 and hotspot_ratio > 0.015
        score = min(30.0, round((mean_diff * 2.2) + (hotspot_ratio * 400), 2)) if suspicious else 0.0
        return ForensicLayerResult(
            layer_name="ela",
            suspicious=suspicious,
            score=score,
            detail=f"mean_diff={mean_diff:.2f}, hotspot_ratio={hotspot_ratio:.4f}",
        )

    def _fft_moire_detection(self, image: Image.Image) -> ForensicLayerResult:
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        gray = cv2.resize(gray, (512, 512))
        spectrum = np.fft.fftshift(np.fft.fft2(gray))
        magnitude = np.log1p(np.abs(spectrum))
        h, w = magnitude.shape
        cy, cx = h // 2, w // 2
        y, x = np.ogrid[:h, :w]
        radius = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        annulus = magnitude[(radius > 70) & (radius < 190)]
        if annulus.size == 0:
            peak_ratio = 0.0
        else:
            peak_ratio = float(np.mean(annulus > (np.mean(annulus) + (2.8 * np.std(annulus)))))
        suspicious = peak_ratio > 0.028
        score = min(25.0, round(peak_ratio * 500, 2)) if suspicious else 0.0
        return ForensicLayerResult(
            layer_name="fft_moire",
            suspicious=suspicious,
            score=score,
            detail=f"peak_ratio={peak_ratio:.4f}",
        )

    def _ai_artifact_detection(self, image: Image.Image) -> ForensicLayerResult:
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY).astype(np.float32)
        checker_kernel = np.array([[1, -1], [-1, 1]], dtype=np.float32)
        checker = cv2.filter2D(gray, -1, checker_kernel)
        checker_score = float(np.mean(np.abs(checker)))
        lap_var = float(cv2.Laplacian(gray, cv2.CV_32F).var())
        suspicious = checker_score > 18 and lap_var < 2600
        score = min(25.0, round((checker_score / 2.5) + max(0.0, (2600 - lap_var) / 250), 2)) if suspicious else 0.0
        return ForensicLayerResult(
            layer_name="ai_artifact",
            suspicious=suspicious,
            score=score,
            detail=f"checker_score={checker_score:.2f}, laplacian_var={lap_var:.2f}",
        )

    def _template_profile_check(self, document_type: str, image: Image.Image) -> ForensicLayerResult:
        rules = get_rules()
        components, text_lines, density = self._layout_metrics(image)
        expected = rules.forensics["expected_profiles"][document_type]
        suspicious = not (
            expected["components"][0] <= components <= expected["components"][1]
            and expected["text_lines"][0] <= text_lines <= expected["text_lines"][1]
        )
        score = 18.0 if suspicious else 0.0
        return ForensicLayerResult(
            layer_name="template_profile",
            suspicious=suspicious,
            score=score,
            detail=f"components={components}, text_lines={text_lines}, density={density:.4f}",
        )

    def _text_density_check(self, document_type: str, image: Image.Image) -> ForensicLayerResult:
        rules = get_rules()
        _, _, density = self._layout_metrics(image)
        expected = rules.forensics["expected_profiles"][document_type]["density"]
        suspicious = not (expected[0] <= density <= expected[1])
        distance = min(abs(density - expected[0]), abs(density - expected[1])) if suspicious else 0.0
        score = min(15.0, round(distance * 100, 2)) if suspicious else 0.0
        return ForensicLayerResult(
            layer_name="text_density",
            suspicious=suspicious,
            score=score,
            detail=f"density={density:.4f}, expected_range={expected}",
        )

    def _text_alignment_check(self, image: Image.Image) -> ForensicLayerResult:
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
        rows: list[int] = []
        for index in range(1, num_labels):
            x, y, width, height, area = stats[index]
            if area < 18 or width < 4 or height < 4:
                continue
            rows.append(int(y + (height / 2)))

        if len(rows) < 8:
            return ForensicLayerResult(
                layer_name="text_alignment",
                suspicious=False,
                score=0.0,
                detail="insufficient text components",
            )

        clustered_rows = Counter(int(round(row / 12) * 12) for row in rows)
        dominant_rows = [value for _, value in clustered_rows.most_common(6)]
        alignment_spread = float(pstdev(dominant_rows)) if len(dominant_rows) > 1 else 0.0
        suspicious = alignment_spread > 8.5
        score = min(20.0, round(alignment_spread * 1.7, 2)) if suspicious else 0.0
        return ForensicLayerResult(
            layer_name="text_alignment",
            suspicious=suspicious,
            score=score,
            detail=f"alignment_spread={alignment_spread:.2f}, dominant_rows={dominant_rows}",
        )

    @staticmethod
    def _layout_metrics(image: Image.Image) -> tuple[int, int, float]:
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        num_labels, _, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
        components = 0
        for index in range(1, num_labels):
            _, _, width, height, area = stats[index]
            if area >= 18 and width >= 3 and height >= 3:
                components += 1

        horizontal = np.sum(binary > 0, axis=1)
        active_rows = horizontal > max(8, int(binary.shape[1] * 0.015))
        text_lines = 0
        in_line = False
        for value in active_rows:
            if value and not in_line:
                text_lines += 1
                in_line = True
            elif not value:
                in_line = False

        density = float(np.mean(binary > 0))
        return components, text_lines, density
