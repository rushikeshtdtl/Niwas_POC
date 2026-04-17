package com.niwas.kyc.security;
 
import java.io.IOException;
import java.util.Collections;
 
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
 
import com.niwas.kyc.util.jwtUtil;
 
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
 
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;
 
@Component
public class JwtAuthFilter extends OncePerRequestFilter {
 
    @Autowired
    private jwtUtil jwtUtil;

    private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(JwtAuthFilter.class);
 
    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain)
            throws ServletException, IOException {
 
        // IMPORTANT: Allow preflight requests
        if (request.getMethod().equalsIgnoreCase("OPTIONS")) {
            filterChain.doFilter(request, response);
            return;
        }
 
        String header = request.getHeader("Authorization");
        if (header != null && header.startsWith("Bearer ")) {
            String token = header.substring(7);
            logger.info("JwtAuthFilter: Processing token...");

            boolean valid = jwtUtil.validateJwtToken(token);
            if (!valid) {
                logger.warn("JwtAuthFilter: Invalid token!");
                response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                response.getWriter().write("Invalid JWT Token");
                return;
            }

            String mobile = jwtUtil.getUserNameFromJwtToken(token);
            String name = jwtUtil.getNameFromJwtToken(token);
            logger.info("JwtAuthFilter: Authenticated Mobile: {}, Name: {}", mobile, name);

            UsernamePasswordAuthenticationToken auth = new UsernamePasswordAuthenticationToken(
                    mobile,
                    null,
                    java.util.Collections.emptyList());
            
            auth.setDetails(name);

            SecurityContextHolder.getContext().setAuthentication(auth);
            logger.info("JwtAuthFilter: SecurityContext updated");
        }
 
        filterChain.doFilter(request, response);
    }
}