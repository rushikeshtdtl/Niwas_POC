package com.niwas.kyc.util;

import org.springframework.stereotype.Component;

@Component
public class FuzzyMatcher {

    /**
     * Calculates the similarity between two strings using Levenshtein distance.
     * Returns a percentage (0-100).
     */
    public double calculateSimilarity(String s1, String s2) {
        if (s1 == null || s2 == null) {
            return 0.0;
        }
        
        s1 = s1.toLowerCase().trim();
        s2 = s2.toLowerCase().trim();

        if (s1.equals(s2)) {
            return 100.0;
        }

        int m = s1.length();
        int n = s2.length();
        
        if (m == 0 || n == 0) {
            return 0.0;
        }

        int[][] d = new int[m + 1][n + 1];

        for (int i = 0; i <= m; i++) {
            d[i][0] = i;
        }
        for (int j = 0; j <= n; j++) {
            d[0][j] = j;
        }

        for (int j = 1; j <= n; j++) {
            for (int i = 1; i <= m; i++) {
                int cost = (s1.charAt(i - 1) == s2.charAt(j - 1)) ? 0 : 1;
                d[i][j] = Math.min(Math.min(
                    d[i - 1][j] + 1,      // deletion
                    d[i][j - 1] + 1),     // insertion
                    d[i - 1][j - 1] + cost // substitution
                );
            }
        }

        int distance = d[m][n];
        int maxLen = Math.max(m, n);

        return (1.0 - (double) distance / maxLen) * 100;
    }
}
