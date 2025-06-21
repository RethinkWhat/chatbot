class AdminPanel {
    constructor() {
        this.loginSection = document.getElementById('loginSection');
        this.adminContent = document.getElementById('adminContent');
        this.loginForm = document.getElementById('loginForm');
        this.menuList = document.getElementById('menuList');
        this.menuWindow = document.getElementById('menuWindow');
        this.confirmWindow = document.getElementById('confirmWindow');
        this.menuForm = document.getElementById('menuForm');
        this.statusMessage = document.getElementById('statusMessage');
        
        this.currentEditingId = null;
        this.menuData = {};
        
        this.initializeEventListeners();
        this.checkAuthentication();
    }
    
    initializeEventListeners() {
        // Login form
        this.loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        
        // Toolbar buttons
        document.getElementById('addMenuBtn').addEventListener('click', () => this.showAddMenuWindow());
        document.getElementById('saveAllBtn').addEventListener('click', () => this.saveAllChanges());
        document.getElementById('resetBtn').addEventListener('click', () => this.showResetConfirmation());
        document.getElementById('logoutBtn').addEventListener('click', () => this.logout());
        
        // Popup controls
        document.getElementById('closeWindow').addEventListener('click', () => this.closeMenuWindow());
        document.getElementById('cancelBtn').addEventListener('click', () => this.closeMenuWindow());
        this.menuForm.addEventListener('submit', (e) => this.handleMenuSave(e));
        
        // Confirmation popup
        document.getElementById('confirmCancel').addEventListener('click', () => this.closeConfirmWindow());
        document.getElementById('confirmOk').addEventListener('click', () => this.executeConfirmedAction());
        
        // Close windows on backdrop click
        this.menuWindow.addEventListener('click', (e) => {
            if (e.target === this.menuWindow) this.closeMenuWindow();
        });
        
        this.confirmWindow.addEventListener('click', (e) => {
            if (e.target === this.confirmWindow) this.closeConfirmWindow();
        });
        
        // Escape key to close windows
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeMenuWindow();
                this.closeConfirmWindow();
            }
        });
    }
    
    checkAuthentication() {
        const isAuthenticated = sessionStorage.getItem('slu_admin_auth') === 'true';
        if (isAuthenticated) {
            this.showAdminPanel();
        }
    }
    
    handleLogin(e) {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        // admin credentials to change
        if (username === 'admin' && password === 'admin123') {
            sessionStorage.setItem('slu_admin_auth', 'true');
            this.showAdminPanel();
            this.showStatus('Login successful!', 'success');
        } else {
            this.showStatus('Invalid credentials. Please try again.', 'error');
        }
    }
    
    showAdminPanel() {
        this.loginSection.style.display = 'none';
        this.adminContent.style.display = 'block';
        this.loadMenuData();
        this.renderMenuList();
    }
    
    logout() {
        sessionStorage.removeItem('slu_admin_auth');
        this.adminContent.style.display = 'none';
        this.loginSection.style.display = 'flex';
        document.getElementById('username').value = '';
        document.getElementById('password').value = '';
        this.showStatus('Logged out successfully.', 'info');
    }
    
    loadMenuData() {
        const savedMenu = localStorage.getItem('slu_chatbot_menu');
        if (savedMenu) {
            this.menuData = JSON.parse(savedMenu);
        } else {
            // Load default menu list
            this.menuData = this.getDefaultMenuData();
        }
    }
    
    //Default menu list
    getDefaultMenuData() {
        return {
            "1": {
                title: "Admission Requirements",
                emoji: "📋",
                content: `Learn about who can apply and what you need to be eligible.<br>

<br><strong>Who can apply for the SLU-CEE?</strong><br>

<br>• Filipino applicants (Grade 12 students or graduates from AY 2023-2024, provided they have not enrolled in college).
<br>• Applicants of good moral character and with no violations in school.
<br>• Filipino applicants from foreign schools should send a scanned transcript and preferred program.
<br>• International students need to process their application at the SLU University Registrar's Office and pay a ₱1960 pre-admission fee.
<br>• Persons with disabilities (medical, mental, or psychological) should consult the Director of Counseling and Wellness.
<br>• Alternative Learning System passers must consult the University Registrar before applying.`
            },
            "2": {
                title: "Program Catalog",
                emoji: "📚",
                content: `Explore the various programs and courses we offer.<br>

<br><strong>School of Accountancy, Management, Computing and Information Studies:</strong><br>
<br>&emsp;- Bachelor of Science in Accountancy
<br>&emsp;- Bachelor of Science in Management Accounting
<br>&emsp;- Bachelor of Science in Business Administration Major In:
<br>&emsp;&emsp;- Financial Management with Specialization in Business Analytics
<br>&emsp;&emsp;- Marketing Management with Specialization in Business Analytics
<br>&emsp;- Bachelor of Science in Entrepreneurship
<br>&emsp;- Bachelor of Science in Tourism Management
<br>&emsp;- Bachelor of Science in Hospitality Management
<br>&emsp;- Bachelor of Science in Computer Science
<br>&emsp;- Bachelor of Science in Information Technology
<br>&emsp;- Bachelor of Multimedia Arts<br>

<br><strong>School of Advanced Studies</strong><br>
<br>&emsp;- Accountancy, Business and Management
<br>&emsp;&emsp;- Doctor of Philosophy in Management
<br>&emsp;&emsp;- Master of Business Administration
<br>&emsp;&emsp;- Master of Entrepreneurship
<br>&emsp;&emsp;- Master of Science in Accountancy
<br>&emsp;&emsp;- Master of Science in Business Administration
<br>&emsp;&emsp;- Master in Financial Technology
<br>&emsp;&emsp;- Master of Science in Public Management
<br>&emsp;- Computing and Information Technology
<br>&emsp;&emsp;- Master in Information Technology
<br>&emsp;&emsp;- Master in Library and Information Science
<br>&emsp;&emsp;- Master of Science in Service, Management, and Engineering
<br>&emsp;- Engineering
<br>&emsp;&emsp;- Doctor of Engineering - Research Track
<br>&emsp;&emsp;- Master in Manufacturing Engineering and Management
<br>&emsp;&emsp;- Master of Arts in Environmental and Habitat Planning
<br>&emsp;&emsp;- Master of Engineering Major in Chemical Engineering
<br>&emsp;&emsp;- Master of Engineering Major in Electrical Engineering
<br>&emsp;&emsp;- Master of Engineering Major in Electronics Engineering
<br>&emsp;&emsp;- Master of Engineering Major in Industrial Engineering
<br>&emsp;&emsp;- Master of Engineering Major in Mechanical Engineering
<br>&emsp;&emsp;- Master of Science in Environmental Engineering
<br>&emsp;&emsp;- Master of Science in Management Engineering
<br>&emsp;&emsp;- Diploma in Disaster Risk Management
<br>&emsp;- Liberal Arts
<br>&emsp;&emsp;- Doctor of Philosophy in Philosophy
<br>&emsp;&emsp;- Doctor of Philosophy in Psychology
<br>&emsp;&emsp;- Master of Arts in Philosophy
<br>&emsp;&emsp;- Master of Arts in Religious Studies
<br>&emsp;&emsp;- Master of Science in Guidance and Counseling
<br>&emsp;&emsp;- Master of Science in Psychology
<br>&emsp;- Natural Sciences
<br>&emsp;&emsp;- Doctor of Philosophy in Biology
<br>&emsp;&emsp;- Doctor of Philosophy in Pharmacy
<br>&emsp;&emsp;- Master in Environmental Sciences
<br>&emsp;&emsp;- Master of Science in Biology
<br>&emsp;&emsp;- Master of Science in Environmental Conservation Biology
<br>&emsp;&emsp;- Master of Science in Medical Technology
<br>&emsp;&emsp;- Master of Science in Medical Technology
<br>&emsp;&emsp;- Master of Science in Pharmacy
<br>&emsp;&emsp;- Master of Science in Public Health
<br>&emsp;&emsp;- Master in Public Health
<br>&emsp;- Nursing
<br>&emsp;&emsp;- Doctor of Philosophy in Nursing - Research Track
<br>&emsp;&emsp;- Master of Science in Nursing
<br>&emsp;&emsp;- Master in Nursing Education
<br>&emsp;- Teacher Education
<br>&emsp;&emsp;- Doctor of Philosophy in Education Major in Science Education
<br>&emsp;&emsp;- Doctor of Philosophy in Educational Management
<br>&emsp;&emsp;- Doctor of Philosophy in Language Education
<br>&emsp;&emsp;- Master of Arts in Catholic Educational Leadership and Management
<br>&emsp;&emsp;- Master of Arts in Education Major in Early Childhood Education
<br>&emsp;&emsp;- Master of Arts in Education Major in Filipino Education
<br>&emsp;&emsp;- Master of Arts in Education Major in Inclusive Education
<br>&emsp;&emsp;- Master of Arts in Education Major in Language Education
<br>&emsp;&emsp;- Master of Arts in Education Major in Mathematics Education
<br>&emsp;&emsp;- Master of Arts in Education Major in Science Education
<br>&emsp;&emsp;- Master of Arts in Education Major in Social Studies
<br>&emsp;&emsp;- Master of Arts in Educational Management
<br>&emsp;&emsp;- Master of Arts in Special Education
<br>&emsp;&emsp;- Master of Science in Physical Education
<br>&emsp;&emsp;- Graduate Certificate in Teaching in Medicine<br>

<br><strong>School of Engineering and Architecture:</strong><br>
<br>&emsp;- Bachelor of Science in Architecture
<br>&emsp;- Bachelor of Science in Chemical Engineering
<br>&emsp;- Bachelor of Science in Civil Engineering
<br>&emsp;- Bachelor of Science in Electrical Engineering
<br>&emsp;- Bachelor of Science in Electronics Engineering
<br>&emsp;- Bachelor of Science in Geodetic Engineering
<br>&emsp;- Bachelor of Science in Industrial Engineering
<br>&emsp;- Bachelor of Science in Mechanical Engineering
<br>&emsp;- Bachelor of Science in Mechatronics Engineering
<br>&emsp;- Bachelor of Science in Mining Engineering<br>

<br><strong>School of Law</strong><br>
<br>&emsp;- Juris Doctor (J.D.)
<br>&emsp;- Master of Laws (L.L.M.)<br>

<br><strong>School of Medicine</strong><br>
<br>&emsp;- Doctor of Medicine<br>

<br><strong>School of Nursing, Allied Health and Biological Sciences:</strong><br>
<br>&emsp;- Bachelor of Science in Biology
<br>&emsp;- Bachelor of Science in Medical Laboratory Science
<br>&emsp;- Bachelor of Science in Nursing
<br>&emsp;- Bachelor of Science in Pharmacy
<br>&emsp;- Bachelor of Science in Radiologic Technology<br>

<br><strong>School of Teacher Education and Liberal Arts:</strong><br>
<br>&emsp;- Bachelor of Arts in Communication
<br>&emsp;- Bachelor of Arts in Philosophy
<br>&emsp;- Bachelor of Arts in Political Science
<br>&emsp;- Bachelor of Elementary Education
<br>&emsp;- Bachelor of Physical Education
<br>&emsp;- Bachelor of Science in Psychology
<br>&emsp;- Bachelor of Science in Secondary Education Major In:
<br>&emsp;&emsp;- English
<br>&emsp;&emsp;- Filipino
<br>&emsp;&emsp;- Math
<br>&emsp;&emsp;- Science
<br>&emsp;&emsp;- Social Studies
<br>&emsp;- Bachelor of Special Needs Education
<br>&emsp;- Bachelor of Science in Social Work
<br>&emsp;- Certificate in Teaching`
            },
            "3": {
                title: "Tuition & Fees",
                emoji: "💰",
                content: `Find out about the costs for the SLU-CEE and other fees.<br>

<br><strong>What are the SLU-CEE exam fees?</strong><br>

<br>• ₱550 for Baguio testing.
<br>• ₱750 for satellite testing.<br>

<br>&emsp;<em>Note: The fee is non-refundable.</em>`
            },
            "4": {
                title: "Scholarships & Financial Aid",
                emoji: "🎓",
                content: `Discover available scholarships and financial aid options.<br>

<br><strong>What are the entrance scholarships for SLU-CEE top placers?</strong><br>

<br>• <b>Top 1-10 placers</b>: 100% tuition fee discount (except miscellaneous fees) for the first semester of AY 2025-2026.
<br>• <b>Top 11-100 placers</b>: 50% tuition fee discount (except miscellaneous fees) for the first semester of AY 2025-2026.<br>

<br><strong>SLU offers various scholarships:</strong>
<br>• CHED TES / PESFA
<br>• Cebuana Lhuillier Scholarship
<br>• DOST & CHED Graduate Scholarships
<br>• Bukas Tuition Installment Plans`
            },
            "5": {
                title: "Enrollment Process",
                emoji: "📝",
                content: `Get detailed, step-by-step instructions on how to apply and enroll.<br>

<br><strong>How do I apply for the SLU-CEE?</strong><br>

<br>• Complete the <b>SLU-CEE Application Form</b> online.
<br>• Submit the <b>Principal's Recommendation Form</b> and upload it.
<br>• For SHS graduates of AY 2023-2024, submit the <b>Certificate of Non-release of F137a</b>.
<br>• Pay the SLU-CEE Fee: ₱550 for Baguio testing or ₱750 for satellite testing.
<br>• The <b>SLU-CEE Test Permit</b> is valid until August 2025.`
            },
            "6": {
                title: "Contact Admissions",
                emoji: "📞",
                content: `Reach out for more info or personalized assistance.<br>

<br><strong>How can I get in touch with admissions?</strong><br>

<br>• Email: <b>admissions@slu.edu.ph</b>
<br>• Mobile: <b>09082844467</b><br>

<br>&emsp;<i>Feel free to reach out for specific questions or issues!</i>`
            }
        };
    }
    
    renderMenuList() {
        this.menuList.innerHTML = '';
        
        Object.entries(this.menuData).forEach(([id, item]) => {
            const menuItem = document.createElement('div');
            menuItem.className = 'menu-item';
            menuItem.innerHTML = `
                <div class="menu-item-header">
                    <div class="menu-item-title">
                        <span class="emoji">${item.emoji}</span>
                        <h3>${this.escapeHtml(item.title)}</h3>
                    </div>
                    <div class="menu-item-actions">
                        <button class="action-btn edit" onclick="adminPanel.editMenuItem('${id}')">
                            ✏️ Edit
                        </button>
                        <button class="action-btn delete" onclick="adminPanel.deleteMenuItem('${id}')">
                            🗑️ Delete
                        </button>
                    </div>
                </div>
                <div class="menu-item-content">
                    ${this.formatContentPreview(item.content)}
                </div>
            `;
            this.menuList.appendChild(menuItem);
        });
    }
    
    formatContentPreview(content) {
        const textOnly = content.replace(/<[^>]*>/g, '');
        return textOnly.length > 200 ? textOnly.substring(0, 200) + '...' : textOnly;
    }
    
    showAddMenuWindow() {
        this.currentEditingId = null;
        document.getElementById('windowTitle').textContent = 'Add New Menu Item';
        document.getElementById('menuTitle').value = '';
        document.getElementById('menuEmoji').value = '';
        document.getElementById('menuContent').value = '';
        this.menuWindow.classList.add('active');
    }
    
    editMenuItem(id) {
        this.currentEditingId = id;
        const item = this.menuData[id];
        
        document.getElementById('windowTitle').textContent = 'Edit Menu Item';
        document.getElementById('menuTitle').value = item.title;
        document.getElementById('menuEmoji').value = item.emoji;
        document.getElementById('menuContent').value = item.content;
        this.menuWindow.classList.add('active');
    }
    
    deleteMenuItem(id) {
        this.pendingDeleteId = id;
        const item = this.menuData[id];
        document.getElementById('confirmMessage').textContent = 
            `Are you sure you want to delete "${item.title}"? This action cannot be undone.`;
        this.confirmWindow.classList.add('active');
        this.pendingAction = 'delete';
    }
    
    handleMenuSave(e) {
        e.preventDefault();
        
        const title = document.getElementById('menuTitle').value.trim();
        const emoji = document.getElementById('menuEmoji').value.trim();
        const content = document.getElementById('menuContent').value.trim();
        
        if (!title || !emoji || !content) {
            this.showStatus('Please fill in all fields.', 'error');
            return;
        }
        
        const menuItem = { title, emoji, content };
        
        if (this.currentEditingId) {
            // Edit existing item
            this.menuData[this.currentEditingId] = menuItem;
            this.showStatus('Menu item updated successfully!', 'success');
        } else {
            // Add new item
            const newId = this.generateNewId();
            this.menuData[newId] = menuItem;
            this.showStatus('Menu item added successfully!', 'success');
        }
        
        this.renderMenuList();
        this.closeMenuWindow();
        this.markAsUnsaved();
    }
    
    generateNewId() {
        const existingIds = Object.keys(this.menuData).map(id => parseInt(id));
        return (Math.max(...existingIds, 0) + 1).toString();
    }
    
    closeMenuWindow() {
        this.menuWindow.classList.remove('active');
        this.currentEditingId = null;
    }
    
    closeConfirmWindow() {
        this.confirmWindow.classList.remove('active');
        this.pendingDeleteId = null;
        this.pendingAction = null;
    }
    
    executeConfirmedAction() {
        if (this.pendingAction === 'delete' && this.pendingDeleteId) {
            delete this.menuData[this.pendingDeleteId];
            this.renderMenuList();
            this.showStatus('Menu item deleted successfully!', 'success');
            this.markAsUnsaved();
        } else if (this.pendingAction === 'reset') {
            this.menuData = this.getDefaultMenuData();
            this.renderMenuList();
            this.showStatus('Menu data has been reset to default.', 'info');
            this.markAsUnsaved();
        }
        
        this.closeConfirmWindow();
    }
    
    saveAllChanges() {
        try {
            localStorage.setItem('slu_chatbot_menu', JSON.stringify(this.menuData));
            this.showStatus('All changes saved successfully!', 'success');
            this.markAsSaved();
        } catch (error) {
            this.showStatus('Error saving changes. Please try again.', 'error');
            console.error('Save error:', error);
        }
    }
    
    showResetConfirmation() {
        document.getElementById('confirmMessage').textContent = 
            'Are you sure you want to reset all menu data to default? This will overwrite all current items and cannot be undone.';
        this.confirmWindow.classList.add('active');
        this.pendingAction = 'reset';
    }
    
    markAsUnsaved() {
        const saveBtn = document.getElementById('saveAllBtn');
        saveBtn.textContent = '💾 Save Changes*';
        saveBtn.classList.add('unsaved');
    }
    
    markAsSaved() {
        const saveBtn = document.getElementById('saveAllBtn');
        saveBtn.textContent = '💾 Save Changes';
        saveBtn.classList.remove('unsaved');
    }
    
    showStatus(message, type = 'info') {
        this.statusMessage.textContent = message;
        this.statusMessage.className = `status-message ${type} show`;
        this.statusMessage.style.display = 'block';
        
        if (this.statusTimeout) {
            clearTimeout(this.statusTimeout);
        }

        this.statusTimeout = setTimeout(() => {
            this.statusMessage.classList.remove('show');
            setTimeout(() => {
                this.statusMessage.style.display = 'none';
            }, 300);
        }, 3000);
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.adminPanel = new AdminPanel();
});