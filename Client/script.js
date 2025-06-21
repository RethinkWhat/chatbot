class SLUChatbot {
    constructor() {
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.menuOptions = document.getElementById('menuOptions');
        
        this.isTyping = false;
        this.menuData = this.loadMenuData();
        
        this.initializeEventListeners();
        this.displayCurrentTime();
        this.initializeWelcomeMessage();
    }
    
    loadMenuData() {
        // Load menu list from localStorage or use default
        const savedMenu = localStorage.getItem('slu_chatbot_menu');
        if (savedMenu) {
            return JSON.parse(savedMenu);
        }
        
        // Default menu list
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

<br>&emsp;<i>Feel free to reach out for specific questions or issues!</i>`}
        };
    }
    
    async initializeWelcomeMessage() {
        const staticWelcome = document.querySelector('#chatMessages .message.bot-message');
        if (staticWelcome) {
            staticWelcome.style.display = 'none';
        }
        
        this.menuOptions.style.display = 'none';
        
        await this.showTypingIndicator();
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        messageDiv.innerHTML = `
            <div class="message-content">
                <p>Hello! Welcome to the SLU Enrollment Assistant.</p>
                <p>How can I assist you today?</p>
            </div>
            <div class="message-time">${this.getCurrentTime()}</div>
        `;
        
        this.chatMessages.appendChild(messageDiv);
        this.hideTypingIndicator();
        this.scrollToBottom();
    }
    
    initializeEventListeners() {
        // Send button click
        this.sendBtn.addEventListener('click', () => this.handleSend());
        
        // Enter key press
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSend();
            }
        });
        
        // Menu button clicks
        document.addEventListener('click', (e) => {
            if (e.target.closest('.menu-btn')) {
                const option = e.target.closest('.menu-btn').dataset.option;
                this.handleMenuSelection(option);
            }
            
            if (e.target.closest('.quick-btn')) {
                const action = e.target.closest('.quick-btn').dataset.quick;
                this.handleQuickAction(action);
            }
        });
        
        // Chat input box
        this.chatInput.addEventListener('input', () => {
            this.chatInput.style.height = 'auto';
            this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 100) + 'px';
        });
    }
    
    displayCurrentTime() {
        const now = new Date();
        const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const initialTimeElement = document.getElementById('initialTime');
        if (initialTimeElement) {
            initialTimeElement.textContent = timeString;
        }
    }
    
    // Handles User input or messages
    async handleSend() {
        const message = this.chatInput.value.trim();
        if (!message || this.isTyping) return;
        
        this.addUserMessage(message);
        this.chatInput.value = '';
        this.chatInput.style.height = 'auto';
        
        await this.processMessage(message);
    }
    
    addUserMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user-message';
        messageDiv.innerHTML = `
            <div class="message-content">${this.escapeHtml(message)}</div>
            <div class="message-time">${this.getCurrentTime()}</div>
        `;
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    async addBotMessage(content, showMenu = false) {
        await this.showTypingIndicator();
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        messageDiv.innerHTML = `
            <div class="message-content">${content}</div>
            <div class="message-time">${this.getCurrentTime()}</div>
        `;
        
        this.chatMessages.appendChild(messageDiv);
        
        if (showMenu) {
            this.showMenuOptions();
        }
        
        this.hideTypingIndicator();
        this.scrollToBottom();
    }
    
    async processMessage(message) {
        const lowerMessage = message.toLowerCase();
        
        if (this.isMenuRequest(lowerMessage)) {
            await this.addBotMessage(
                "Here are the available options. Please select one:",
                true
            );
            return;
        }
        
        const response = this.getKeywordResponse(lowerMessage);
        if (response) {
            await this.addBotMessage(response);
            return;
        }

        try{
            console.log("Sending message to server:", message);
            const serverResponse = await fetch('http://localhost:5005/webhooks/rest/webhook', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ "message": message })
            });
            const data = await serverResponse.json();
            console.log("Rasa response:", JSON.stringify(data, null, 2));
            for (const message of data) {
                if (message.text) {
                    await this.addBotMessage(message.text);
                }
            }
        } catch (error) {
            // Fallback response
            console.log(error)
            await this.addBotMessage(
                `Sorry, I didn't understand that. Can you try again? You can type "menu" to see available options or use the quick buttons below.`
            );
        }
    }
    
    // Menu keywords
    isMenuRequest(message) {
        const menuKeywords = ['menu', 'options', 'help', 'start', 'begin', 'show menu'];
        return menuKeywords.some(keyword => message.includes(keyword));
    }
    
    getKeywordResponse(message) {
        // Admission keywords
        if (message.includes('admission') || message.includes('requirement') || message.includes('apply') || message.includes('eligible')) {
            return this.menuData["1"].content;
        }
        
        // Program keywords
        if (message.includes('program') || message.includes('course') || message.includes('degree') || message.includes('major')) {
            return this.menuData["2"].content;
        }
        
        // Fee keywords
        if (message.includes('fee') || message.includes('cost') || message.includes('tuition') || message.includes('price')) {
            return this.menuData["3"].content;
        }
        
        // Scholarship keywords
        if (message.includes('scholarship') || message.includes('financial aid') || message.includes('discount')) {
            return this.menuData["4"].content;
        }
        
        // Enrollment keywords
        if (message.includes('enroll') || message.includes('registration') || message.includes('process')) {
            return this.menuData["5"].content;
        }
        
        // Contact keywords
        if (message.includes('contact') || message.includes('mobile') || message.includes('phone') || message.includes('email') || message.includes('reach')) {
            return this.menuData["6"].content;
        }
        
        return null;
    }
    
    async handleMenuSelection(option) {
        const menuItem = this.menuData[option];
        if (menuItem) {
            this.addUserMessage(menuItem.title);
            await this.addBotMessage(menuItem.content);
            
            this.hideMenuOptions();
        }
    }
    
    async handleQuickAction(action) {
        switch (action) {
            case 'menu':
                this.addUserMessage("Show Menu");
                await this.addBotMessage(
                    "Here are the available options. Please select one:",
                    true
                );
                break;
            case 'help':
                this.addUserMessage("Help");
                await this.addBotMessage(
                    `I'm here to help with your SLU enrollment questions! You can:
                    
<br>• Click on the menu buttons when available
<br>• Type keywords like "admission", "programs", "fees", etc.
<br>• Ask specific questions about enrollment
<br>• Type "menu" anytime to see all options<br>

<br>What would you like to know about?`
                );
                break;
        }
    }
    
    showMenuOptions() {
        const menuGrid = this.menuOptions.querySelector('.menu-grid');
        menuGrid.innerHTML = '';
        
        Object.entries(this.menuData).forEach(([key, item]) => {
            const button = document.createElement('button');
            button.className = 'menu-btn';
            button.dataset.option = key;
            button.innerHTML = `
                <span class="menu-emoji">${item.emoji}</span>
                <span class="menu-text">${item.title}</span>
            `;
            menuGrid.appendChild(button);
        });
        
        const lastBotMessage = [...this.chatMessages.querySelectorAll('.bot-message')].pop();
        if (lastBotMessage) {
            lastBotMessage.appendChild(this.menuOptions);
        }
        
        this.menuOptions.style.display = 'block';
        this.scrollToBottom();
    }
    
    hideMenuOptions() {
        this.menuOptions.style.display = 'none';
    }
    
    async showTypingIndicator() {
        this.isTyping = true;
        this.typingIndicator.classList.add('active');
        this.scrollToBottom();
        
        await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 1000));
    }
    
    hideTypingIndicator() {
        this.isTyping = false;
        this.typingIndicator.classList.remove('active');
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }
    
    getCurrentTime() {
        return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    refreshMenuData() {
        this.menuData = this.loadMenuData();
        if (this.menuOptions.style.display !== 'none') {
            this.showMenuOptions();
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.sluChatbot = new SLUChatbot();
    
    window.addEventListener('storage', (e) => {
        if (e.key === 'slu_chatbot_menu') {
            window.sluChatbot.refreshMenuData();
        }
    });
});