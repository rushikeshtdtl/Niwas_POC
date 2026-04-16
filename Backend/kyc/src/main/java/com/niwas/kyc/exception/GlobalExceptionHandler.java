package com.niwas.kyc.exception;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(org.springframework.web.multipart.support.MissingServletRequestPartException.class)
    public ResponseEntity<ErrorResponse> handleMissingPart(
            org.springframework.web.multipart.support.MissingServletRequestPartException e) {
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(new ErrorResponse("All documents are required"));
    }

    @ExceptionHandler(RuntimeException.class)
    public ResponseEntity<ErrorResponse> handleRuntimeException(RuntimeException e) {
        String message = e.getMessage();
        HttpStatus status = HttpStatus.BAD_REQUEST;
        if (message.contains("Unauthorized") || message.contains("Invalid JWT")) {
            status = HttpStatus.UNAUTHORIZED;
        }
        return ResponseEntity.status(status).body(new ErrorResponse(message));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleException(Exception e) {
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(new ErrorResponse("Internal server error"));
    }
}