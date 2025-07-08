// script.js

class SLUChatbot {
  constructor() {
    //uginx proxy
        this.defaultBackendPort = 8000;
        this.protocol = window.location.protocol;
        this.hostname = window.location.hostname;
        this.actionsURL = `${this.protocol}//${this.hostname}:${this.defaultBackendPort}`;
    this.chatMessages     = document.getElementById('chatMessages');
    this.chatInput        = document.getElementById('chatInput');
    this.sendBtn          = document.getElementById('sendBtn');
    this.stopBtn = document.getElementById('stopBtn');
    this.typingIndicator  = document.getElementById('typingIndicator');
    this.menuOptions      = document.getElementById('menuOptions');

    this.isTyping = false;
    this.abortController = null;
    this.menuData = {};
  }
  async init() {
        // Load menu data from server
        await this.loadMenuData(); //load menu on startup
        this.menuOptions.style.display = 'none'; //hide menu options initially (just for debugging in console)
        this.initializeEventListeners();
        this.displayCurrentTime();
        this.initializeWelcomeMessage();
  }
  // Fetch menu data from your database via backend API
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
  // Show initial bot greeting
  async initializeWelcomeMessage() {
    const firstBotMsg = document.querySelector('#chatMessages .bot-message');
    if (firstBotMsg) firstBotMsg.style.display = 'none';

    this.menuOptions.style.display = 'none';
    await this.showTypingIndicator();

    const div = document.createElement('div');
    div.className = 'message bot-message';
    div.innerHTML = `
      <div class="message-content">
        <p>Hi there! I'm Navi, your go-to guide for Saint Louis University–Baguio.</p>
        <p>How can I assist you today?</p>
      </div>
      <div class="message-time">${this.getCurrentTime()}</div>
    `;
    this.chatMessages.appendChild(div);
    this.hideTypingIndicator();
    this.scrollToBottom();
  }
  initializeEventListeners() {
    this.sendBtn.addEventListener('click', () => this.handleSend());
    this.chatInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.handleSend();
      }
    });

    document.addEventListener('click', (e) => {
      const mb = e.target.closest('.menu-btn');
      if (mb) return this.handleMenuSelection(mb.dataset.optionId);

      const qb = e.target.closest('.quick-btn');
      if (qb) return this.handleQuickAction(qb.dataset.quick);
    });

    this.chatInput.addEventListener('input', () => {
      this.chatInput.style.height = 'auto';
      this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 100) + 'px';
    });
  }
  displayCurrentTime() {
    const now = new Date();
    const t = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const init = document.getElementById('initialTime');
    if (init) init.textContent = t;
  }
  async handleSend() {
    const msg = this.chatInput.value.trim();
    if (!msg || this.isTyping) return;

    this.addUserMessage(msg);
    this.chatInput.value = '';
    this.chatInput.style.height = 'auto';
    this.toggleButtons(true); //set the stop button frontend
    await this.processMessage(msg);
  }
  addUserMessage(msg) {
    const div = document.createElement('div');
    div.className = 'message user-message';
    div.innerHTML = `
      <div class="message-content">${this.escapeHtml(msg)}</div>
      <div class="message-time">${this.getCurrentTime()}</div>
    `;
    this.chatMessages.appendChild(div);
    this.scrollToBottom();
  }
  async addBotMessage(content, showMenu = false) {
    await this.showTypingIndicator();

    const div = document.createElement('div');
    div.className = 'message bot-message';
    div.innerHTML = `
      <div class="message-content">${content}</div>
      <div class="message-time">${this.getCurrentTime()}</div>
    `;
    this.chatMessages.appendChild(div);

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
        const fixList = (raw) => {
            // Ensure each course starts on a new line with "- "
            //use a bunch of ifs to encapsulate  
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
  isMenuRequest(msg) {
    const keys = ['menu', 'options', 'help', 'start'];
    return keys.some(k => msg.includes(k));
  }
  getKeywordResponse(msg) {
    for (const id in this.menuData) {
      const item = this.menuData[id];
      // Here, backend MenuItem should include 'keywords' array or string
      const keywords = item.keywords?.split(',').map(s => s.trim().toLowerCase()) || [];
      if (keywords.some(k => msg.includes(k))) {
        return item.content;
      }
    }
    return null;
  }
  async handleMenuSelection(optionId) {
    const item = this.menuData.menu.find(m => m.id == optionId);
    if (!item) return;

    this.addUserMessage(item.title);
    await this.addBotMessage(item.content);  // Show corresponding content
    this.hideMenuOptions();
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
                await this.addBotMessage("You can ask about admission, programs, fees, enrollment, and more. Type 'menu' anytime.");
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
  hideTypingIndicator() {
    this.isTyping = false;
    this.typingIndicator.classList.remove('active');
  }
  scrollToBottom() {
    setTimeout(() => {
      this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }, 50);
  }
  getCurrentTime() {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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