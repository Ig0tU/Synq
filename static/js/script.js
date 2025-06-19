document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            // Get the current theme from the HTML data attribute
            const currentTheme = document.documentElement.getAttribute('data-theme');
            let newTheme = 'dark'; // Default to dark

            // Determine the new theme
            if (currentTheme === 'dark') {
                newTheme = 'light';
            } else {
                newTheme = 'dark';
            }

            // Update the data-theme attribute
            document.documentElement.setAttribute('data-theme', newTheme);

            // Send a request to Flask to save the theme preference in the session
            // This ensures the theme persists even after page reloads
            fetch(`/toggle_theme?current_page=${encodeURIComponent(window.location.pathname)}`, {
                method: 'GET' // Or 'POST' if you prefer for state changes
            })
            .then(response => {
                // If you want to handle a response from the server, do it here
                // For a simple theme toggle, the server response might not be critical
            })
            .catch(error => {
                console.error('Error toggling theme on server:', error);
            });
        });
    }

    // Example of another micro-interaction: Animate elements on scroll (simple reveal)
    const fadeInElements = document.querySelectorAll('.fade-in');

    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target); // Stop observing once visible
            }
        });
    }, {
        threshold: 0.1 // Trigger when 10% of the element is visible
    });

    fadeInElements.forEach(element => {
        observer.observe(element);
    });

    // Add a simple hover effect for social links in the footer (already handled by CSS, but good for JS examples)
    const socialLinks = document.querySelectorAll('.social-links a');
    socialLinks.forEach(link => {
        link.addEventListener('mouseover', () => {
            link.style.transform = 'scale(1.2)';
            link.style.color = 'var(--primary-color)';
        });
        link.addEventListener('mouseout', () => {
            link.style.transform = 'scale(1)';
            link.style.color = 'var(--header-footer-text)'; /* Reset to default footer text color */
        });
    });
});