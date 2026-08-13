document.addEventListener('DOMContentLoaded', function() {
    
    // 1. Handle Teacher Registration Alert
    const registrationForm = document.querySelector('form[action="/register"]');
    if (registrationForm) {
        registrationForm.addEventListener('submit', function() {
            alert("Thank you for registering! Your profile will now be visible to parents.");
        });
    }

    // 2. Simple Search Button Loading State
    const searchForm = document.querySelector('form[action="/"]');
    if (searchForm) {
        searchForm.addEventListener('submit', function() {
            const btn = this.querySelector('button');
            btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Searching...';
            btn.disabled = true;
        });
    }

    // 3. Optional: Add dynamic area suggestions (Bhopal Specific)
    const areaInput = document.querySelector('input[name="area"]');
    if (areaInput) {
        areaInput.addEventListener('focus', function() {
            console.log("Tip: Popular areas in Bhopal include Indrapuri, MP Nagar, and Arera Colony.");
        });
    }
});





    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    const htmlElement = document.documentElement;

    // 1. Check karein ki pehle se koi theme saved hai?
    const currentTheme = localStorage.getItem('theme') || 'light';
    
    // Initial Setup
    htmlElement.setAttribute('data-theme', currentTheme);
    updateToggleUI(currentTheme);

    // 2. Click Event Listener
    themeToggle.addEventListener('click', () => {
        const activeTheme = htmlElement.getAttribute('data-theme');
        const newTheme = (activeTheme === 'light') ? 'dark' : 'light';
        
        // Theme Apply Karein
        htmlElement.setAttribute('data-theme', newTheme);
        // Browser memory mein save karein
        localStorage.setItem('theme', newTheme);
        
        // Icon aur Button update karein
        updateToggleUI(newTheme);
    });

    // 3. UI Update Function
    function updateToggleUI(theme) {
        if (theme === 'dark') {
            themeIcon.classList.replace('bi-moon-stars', 'bi-sun');
            themeToggle.classList.replace('btn-outline-secondary', 'btn-outline-warning');
            themeToggle.title = "Switch to Light Mode";
        } else {
            themeIcon.classList.replace('bi-sun', 'bi-moon-stars');
            themeToggle.classList.replace('btn-outline-warning', 'btn-outline-secondary');
            themeToggle.title = "Switch to Dark Mode";
        }
    }

    // 4. Smooth Transition (Optional Fix)
    // Isse theme change hote waqt colors ekdum se nahi badlenge, balki fade honge
    document.body.style.transition = "background-color 0.3s ease, color 0.3s ease";




    // --- THEME PERSISTENCE LOGIC ---

// 1. Page load hote hi check karein ki pehle se koi theme saved hai?
document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateToggleIcons(savedTheme);
});

// 2. Theme Toggle Function (Ise apne button ke onclick par lagayein)
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    // Theme apply karein
    document.documentElement.setAttribute('data-theme', newTheme);
    
    // Browser memory (localStorage) mein save karein
    localStorage.setItem('theme', newTheme);
    
    updateToggleIcons(newTheme);
}

// 3. Icons ko update karne ke liye (Optional: agar moon/sun icons hain)
function updateToggleIcons(theme) {
    const darkIcons = document.querySelectorAll('.dark-icon');
    const lightIcons = document.querySelectorAll('.light-icon');
    
    if (theme === 'dark') {
        darkIcons.forEach(el => el.classList.add('d-none'));
        lightIcons.forEach(el => el.classList.remove('d-none'));
    } else {
        darkIcons.forEach(el => el.classList.remove('d-none'));
        lightIcons.forEach(el => el.classList.add('d-none'));
    }
}