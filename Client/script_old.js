class SLUChatbot {
    constructor() {
        //uginx proxy
        this.defaultBackendPort = 8000;
        this.protocol = window.location.protocol;
        this.hostname = window.location.hostname;
        this.actionsURL = `${this.protocol}//${this.hostname}:${this.defaultBackendPort}`;
        //this.acionsURL = window.location.origin;


        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.stopBtn = document.getElementById('stopBtn');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.menuOptions = document.getElementById('menuOptions');
        this.isTyping = false;
        this.abortController = null;
    }

    async init() {
        // Load menu data from server
        await this.loadMenuData(); //load menu on startup
        this.menuOptions.style.display = 'none'; //hide menu options initially (just for debugging in console)
        this.initializeEventListeners();
        this.displayCurrentTime();
        this.initializeWelcomeMessage();
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
        // Send button click/ stop button click
        this.sendBtn.addEventListener('click', () => this.handleSend());
        this.stopBtn.addEventListener('click', () => this.handleStop());

        
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
                const button = e.target.closest('.menu-btn');
                const optionId = button.dataset.optionId;
                const content = button.dataset.content;
                const title = button.querySelector('.menu-text').textContent;

                (async () => {
                    this.addUserMessage(title);
                    await this.addBotMessage(content);  // Use raw HTML directly
                    this.hideMenuOptions();
                })();
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

    handleStop() {
        if (this.abortController) {
            this.abortController.abort();  // Immediately cancel any ongoing fetch
            this.abortController = null;   // Reset
        }
        fetch(`${this.ragServer}/stop`, {
            method: "POST"
        })
        .then(res => res.json())
        .then(data => {
            console.log("Stop requested:", data);
            this.hideTypingIndicator();
            this.toggleButtons(false);
        })
        .catch(err => {
            console.error("Stop request failed:", err);
        });
    }

    toggleButtons(isBotGenerating) {
        this.sendBtn.style.display = isBotGenerating ? "none" : "inline-block";
        this.stopBtn.style.display = isBotGenerating ? "inline-block" : "none";
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
        this.toggleButtons(true); // Show stop button

        
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

        if (showMenu) this.showMenuOptions();

        this.hideTypingIndicator();
        this.scrollToBottom();
    }  
    async processMessage(message) {
    try {
        this.abortController = new AbortController();
        const signal = this.abortController.signal;

        const response = await fetch("http://localhost:5005/webhooks/rest/webhook", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ sender: "user", message }),
            signal
        });

        const data = await response.json();

        // for (const item of data) {
        //     if (item.text) {
        //         const rawMarkdown = `
        // ### Computer Science Subjects
        // - CSE 10: Advanced Computer Architecture
        // - CSE 11: Advanced Operating Systems
        // - CSE 12: Advanced Information Management
        //         `.trim();
        
        //         const parsed = marked.parse(rawMarkdown);
        //         await this.addBotMessage(parsed);
        //     }
        // }
        const fixList = (raw) => {
            // Ensure each course starts on a new line with "- "
            return raw
                .split('-')
                .map(line => line.trim())
                .filter(line => line.length > 0)
                .map(line => `- ${line}`)
                .join('\n');
        };

        for (const item of data) {
            if (item.text) {
                const rawMarkdown = item.text.includes("-") ?  fixList(item.text.trim()) : item.text.trim();
               // await this.addBotMessage(item.text);
               const parsed = marked.parse(rawMarkdown)
               await this.addBotMessage(parsed);
            }
        }

        this.toggleButtons(false);
        this.isTyping = false;
    } catch (error) {
        console.error("Error contacting Rasa:", error);
        //await this.addBotMessage("Sorry, something went wrong.");
        this.toggleButtons(false);
        this.isTyping = false;
    }
    }
    // Menu keywords
    isMenuRequest(message) {
        const menuKeywords = ['menu', 'options', 'help', 'start', 'begin', 'show menu'];
        return menuKeywords.some(keyword => message.includes(keyword));
    }
    async handleMenuSelection(optionId) {
        const selected = this.menuData.menu.find(item => item.id == optionId);
        if (selected) {
            this.addUserMessage(selected.title);
            await this.addBotMessage(selected.content);
            this.hideMenuOptions();
        }
    }
    async handleQuickAction(action) {
        switch (action) {
            case 'menu':
            this.addUserMessage("Show Menu");
            try {
                const response = await fetch("http://localhost:5005/webhooks/rest/webhook", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ message: "menu" })  // triggers intent: show_menu
                });
                const data = await response.json();
                for (const message of data) {
                    if (message.text) {
                        await this.addBotMessage(message.text);
                    }
                }
                await this.showMenuOptions(); // menu is shown after bot message

            } catch (err) {
                console.error("Error fetching dynamic menu:", err);
                await this.addBotMessage("Sorry, I couldn’t load the menu.");
            }
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

        this.menuData.menu.forEach(item => {
            const button = document.createElement('button');
            button.className = 'menu-btn';
            button.dataset.optionId = item.id;
            button.dataset.content = item.content;
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
    async loadMenuData() {
        try {
            const res = await fetch(`${this.actionsURL}/menu`);
            const data = await res.json();

            if (!data.menu) {
                throw new Error("Menu data is missing");
            }

            this.menuData = data;
            console.log("Menu data loaded:", this.menuData);

            if (this.menuOptions.style.display !== 'none') {
                this.showMenuOptions();
            }
        } catch (error) {
            console.error(">< Failed to load menu data from server:", error);
            this.menuData = { menu: [] }; // fallback to empty to avoid crashes
        }
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
    async refreshMenuData() {
        await this.loadMenuData();
        if (this.menuOptions.style.display !== 'none') {
            this.showMenuOptions();
        }
    }
}
document.addEventListener('DOMContentLoaded', async () => {
    window.sluChatbot = new SLUChatbot();
    await window.sluChatbot.init();
    window.addEventListener('storage', async (e) => {
        if (e.key === 'slu_chatbot_menu') {
            await window.sluChatbot.refreshMenuData();
        }
    });

});

