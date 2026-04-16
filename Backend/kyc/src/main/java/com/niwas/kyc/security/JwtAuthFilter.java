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
 
            boolean valid = jwtUtil.validateJwtToken(token);
 
            if (!valid) {
                response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                response.getWriter().write("Invalid JWT Token");
                return;
            }
 
            String mobile = jwtUtil.getUserNameFromJwtToken(token);
 
            UsernamePasswordAuthenticationToken auth = new UsernamePasswordAuthenticationToken(
                    mobile,
                    null,
                    Collections.emptyList());
 
            SecurityContextHolder.getContext().setAuthentication(auth);
        }
 
        filterChain.doFilter(request, response);
    }
}