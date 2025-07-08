//clear session if this is a brand new visit (no referrer or navigation type = reload)
const navType = performance.getEntriesByType("navigation")[0]?.type;

if (!document.referrer && navType !== "navigate") {
    sessionStorage.removeItem('slu_admin_auth');
    console.log("[ADMIN] Session cleared on fresh load.");
} else {
    console.log("[ADMIN] Preserving session.");
}
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
    this.pendingDeleteId = null;
    this.pendingAction = null;

    this.emojiOptions = [
      '🎓', '📚', '🏫', '💼', '📝', '💡', '📅', '🏛️', '💰', '🚌',
      '🍔', '🏥', '🌐', '📞', '✅'
    ];

    this.menuEmojiSelect = document.getElementById('menuEmoji');

    this.initializeEventListeners();
    this.checkAuthentication();
  }

  initializeEventListeners() {
    this.loginForm.addEventListener('submit', (e) => this.handleLogin(e));
    document.getElementById('addMenuBtn').addEventListener('click', () => this.showAddMenuWindow());
    document.getElementById('saveAllBtn').addEventListener('click', () => this.saveAllChanges());
    document.getElementById('resetBtn').addEventListener('click', () => this.showResetConfirmation());
    document.getElementById('logoutBtn').addEventListener('click', () => this.logout());
    document.getElementById("scrapeBtn").addEventListener("click", () => {
      window.location.href = "scrape.html"; // or any correct path to scrape interface
    });
    document.getElementById('closeWindow').addEventListener('click', () => this.closeMenuWindow());
    document.getElementById('cancelBtn').addEventListener('click', () => this.closeMenuWindow());
    this.menuForm.addEventListener('submit', (e) => this.handleMenuSave(e));

    document.getElementById('confirmCancel').addEventListener('click', () => this.closeConfirmWindow());
    document.getElementById('confirmOk').addEventListener('click', () => this.executeConfirmedAction());

    this.menuWindow.addEventListener('click', (e) => {
      if (e.target === this.menuWindow) this.closeMenuWindow();
    });
    this.confirmWindow.addEventListener('click', (e) => {
      if (e.target === this.confirmWindow) this.closeConfirmWindow();
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.closeMenuWindow();
        this.closeConfirmWindow();
      }
    });
  }

  // async checkAuthentication() {
  //   try {
  //     const resp = await fetch('admin_controller.php?action=list', {
  //       credentials: 'same-origin',
  //     });
  //     const text = await resp.text();
  //     console.log('Raw checkAuthentication response:', text);

  //     if (!text) {
  //       console.error('Empty response from server.');
  //       return;
  //     }

  //     const json = JSON.parse(text);
  //     if (json.status === 'success') {
  //       this.menuData = json.data.reduce((acc, item) => {
  //         acc[item.id] = item;
  //         return acc;
  //       }, {});
  //       this.showAdminPanel();
  //     } else {
  //       console.warn('Authentication check failed or no menu data:', json.message);
  //       this.showLoginPanel();
  //     }
  //   } catch (err) {
  //     console.error('Failed to parse or fetch:', err);
  //     this.showLoginPanel();
  //   }
  // }
  async checkAuthentication() {
    const isAuthenticated = sessionStorage.getItem('slu_admin_auth') === 'true';
      if (isAuthenticated) {
        this.showAdminPanel();
      }
  }

  // async handleLogin(e) {
  //   e.preventDefault();
  //   const form = new FormData(this.loginForm);
  //   try {
  //     const resp = await fetch('admin_controller.php?action=login', {
  //       method: 'POST',
  //       body: form,
  //       credentials: 'same-origin',
  //     });
  //     const text = await resp.text();
  //     console.log('Raw login response:', text);
  //     const json = JSON.parse(text);
  //     if (json.status === 'success') {
  //       this.showStatus(json.message, 'success');
  //       await this.checkAuthentication();
  //     } else {
  //       this.showStatus(json.message, 'error');
  //     }
  //   } catch (err) {
  //     console.error('Login error:', err);
  //     this.showStatus('Login failed: Invalid server response.', 'error');
  //   }
  // }

  // showAdminPanel() {
  //   this.loginSection.style.display = 'none';
  //   this.adminContent.style.display = 'block';
  //   this.renderMenuList();
  // }

  // showLoginPanel() {
  //   this.adminContent.style.display = 'none';
  //   this.loginSection.style.display = 'flex';
  // }

  // async logout() {
  //     try {
  //       await fetch('admin_controller.php?action=logout', {
  //         method: 'GET', // send GET request to logout
  //         credentials: 'same-origin',
  //       });
  //       this.menuData = {};
  //       this.showLoginPanel();
  //       this.showStatus('Logged out successfully.', 'info');
  //       this.menuList.innerHTML = '';
  //     } catch (error) {
  //       console.error('Logout failed:', error);
  //       this.showStatus('Logout failed. Please try again.', 'error');
  //     }
  //   }

  // async loadMenu() {
  //   try {
  //     const resp = await fetch('admin_controller.php?action=list');
  //     if (!resp.ok) throw new Error('Failed to load menu');
  //     const json = await resp.json();
  //     if (json.status === 'success') {
  //       this.menuData = json.data.reduce((acc, item) => {
  //         acc[item.id] = item;
  //         return acc;
  //       }, {});
  //       this.renderMenuList();
  //     } else {
  //       console.error('Error loading menu:', json.message);
  //     }
  //   } catch (err) {
  //     console.error('Fetch error:', err);
  //   }
  // }

  async handleLogin(e) {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;

            try {
                const res = await fetch("http://localhost:8000/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username, password })
                });

                const data = await res.json();

                if (res.ok && data.status === "success") {
                    sessionStorage.setItem('slu_admin_auth', 'true');
                    this.showAdminPanel();
                    this.showStatus('Login successful!', 'success');
                } else {
                    this.showStatus(data.detail || 'Login failed.', 'error');
                }
            } catch (err) {
                this.showStatus('Server error during login.', 'error');
                console.error("Login error:", err);
            }
  }

        
  async showAdminPanel() {
            this.loginSection.style.display = 'none';
            this.adminContent.style.display = 'block';
            this.loadMenuData().then(() => this.renderMenuList());
  }

        
  async logout() {
            sessionStorage.removeItem('slu_admin_auth');
            this.adminContent.style.display = 'none';
            this.loginSection.style.display = 'flex';
            document.getElementById('username').value = '';
            document.getElementById('password').value = '';
            this.showStatus('Logged out successfully.', 'info');
  }
  scrape(){
    window.location.href = "scrape.html";
  }
        
  async loadMenuData() {
            try {
                const res = await fetch("http://localhost:8000/admin/menu");
                const data = await res.json();
                this.menuData = {};
                for (const item of data.menu) {
                    this.menuData[item.id] = item;
                }
                console.log("[ADMIN] Loaded menu data from DB:", this.menuData);
            } catch (error) {
                console.error("[ADMIN] Failed to fetch menu items:", error);
                this.menuData = {};
            }
  }
  renderMenuList() {
    this.menuList.innerHTML = '';
    if (Object.keys(this.menuData).length === 0) {
      this.menuList.innerHTML = '<p>No menu items found.</p>';
      return;
    }
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
            <button class="action-btn edit" onclick="adminPanel.editMenuItem('${id}')">✏️ Edit</button>
            <button class="action-btn delete" onclick="adminPanel.deleteMenuItem('${id}')">🗑️ Delete</button>
          </div>
        </div>
        <div class="menu-item-content">${this.formatContentPreview(item.content)}</div>
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
    this.menuForm.reset();
    this.populateEmojiDropdown();
    this.menuWindow.classList.add('active');
  }

  editMenuItem(id) {
    this.currentEditingId = id;
    const item = this.menuData[id];
    if (!item) return;
    document.getElementById('windowTitle').textContent = 'Edit Menu Item';
    document.getElementById('menuTitle').value = item.title;
    this.populateEmojiDropdown(item.emoji);
    document.getElementById('menuContent').value = item.content;
    this.menuWindow.classList.add('active');
  }

  populateEmojiDropdown(selectedEmoji = null) {
    this.menuEmojiSelect.innerHTML = '';
    this.emojiOptions.forEach((emoji) => {
      const option = document.createElement('option');
      option.value = emoji;
      option.textContent = emoji;
      if (emoji === selectedEmoji) option.selected = true;
      this.menuEmojiSelect.appendChild(option);
    });
  }

  async handleMenuSave(e) {
    e.preventDefault();
    const title = document.getElementById('menuTitle').value.trim();
    const emoji = this.menuEmojiSelect.value;
    const content = document.getElementById('menuContent').value.trim();

    if (!title || !emoji || !content) {
      this.showStatus('Please fill in all fields.', 'error');
      return;
    }

    const menuItem = { title, emoji, content };

            if (this.currentEditingId) {
                // Editing
                this.menuData[this.currentEditingId] = {
                    ...this.menuData[this.currentEditingId], // retain ID or any other keys
                    ...menuItem
                };
                delete this.menuData[this.currentEditingId].isNew; // ensure it's treated as existing
                console.log(`[ADMIN] Edited item ${this.currentEditingId}:`, this.menuData[this.currentEditingId]);
            } else {
                // Adding new item
                const newId = this.generateNewId();
                menuItem.isNew = true;
                this.menuData[newId] = menuItem;
                console.log(`[ADMIN] Added new item ${newId}:`, menuItem);
            }

            this.renderMenuList();
            this.closeMenuWindow();
            this.markAsUnsaved();
  }
  generateNewId() {
    const existingIds = Object.keys(this.menuData).map(id => parseInt(id));
    return (Math.max(...existingIds, 0) + 1).toString();
  }

  deleteMenuItem(id) {
    this.pendingDeleteId = id;
    const item = this.menuData[id];
    console.log(`Delete requested for item ID ${id}:`, item);
    document.getElementById('confirmMessage').textContent = 
      `Are you sure you want to delete "${item.title}"? This action cannot be undone.`;
    this.confirmWindow.classList.add('active');
    this.pendingAction = 'delete';
    console.log(`Confirmed deletion of item ${this.pendingDeleteId}`);
  }

  async executeConfirmedAction() {
    if (this.pendingAction === 'delete' && this.pendingDeleteId) {
      try {
        const res = await fetch(`http://localhost:8000/admin/menu/${this.pendingDeleteId}`, {
          method: "DELETE"
        });
        console.log(`[ADMIN] Deleted item ${this.pendingDeleteId}:`, await res.json());
      } catch (err) {
        console.error(`[ADMIN] Failed to delete item ${this.pendingDeleteId}`, err);
      }
      delete this.menuData[this.pendingDeleteId];
      this.renderMenuList();
      this.showStatus('Menu item deleted successfully!', 'success');
      this.markAsUnsaved();
    }
  }

  showConfirmWindow(message) {
    document.getElementById('confirmMessage').textContent = message;
    this.confirmWindow.classList.add('active');
  }

  closeConfirmWindow() {
    this.confirmWindow.classList.remove('active');
    this.pendingDeleteId = null;
    this.pendingAction = null;
  }

  closeMenuWindow() {
    this.menuWindow.classList.remove('active');
    this.currentEditingId = null;
    this.menuForm.reset();
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


  showResetConfirmation() {
    this.pendingAction = 'reset';
    this.showConfirmWindow('Are you sure you want to reset all menu items to default? This cannot be undone.');
  }

  async resetMenu() {
    try {
      const resp = await fetch('admin_controller.php?action=reset', {
        method: 'POST',
        credentials: 'same-origin',
      });
      const json = await resp.json();
      if (json.status === 'success') {
        this.menuData = json.data.reduce((acc, item) => {
          acc[item.id] = item;
          return acc;
        }, {});
        this.renderMenuList();
        this.showStatus('Menu reset to default.', 'success');
      } else {
        this.showStatus(json.message || 'Reset failed.', 'error');
      }
    } catch (err) {
      console.error(err);
      this.showStatus('Error resetting menu.', 'error');
    }
  }

  async saveAllChanges() {
    try {
      const entries = Object.entries(this.menuData);

      for (const [id, item] of entries) {
        if (item.isNew) {
          const res = await fetch("http://localhost:8000/admin/menu", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(item)
          });
          const result = await res.json();
          console.log(`[ADMIN] Created item:`, result);
        } else {
          const res = await fetch(`http://localhost:8000/admin/menu/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(item)
          });
          const result = await res.json();
          console.log(`[ADMIN] Updated item ${id}:`, result);
        }
      }

      this.showStatus('All changes saved successfully!', 'success');
      this.markAsSaved();

      // Optional: refetch from DB to verify
      await this.loadMenuData();
      this.renderMenuList();

      } catch (error) {
        console.error("[ADMIN] Save error:", error);
        this.showStatus('Error saving changes to backend.', 'error');
      }
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

  escapeHtml(text) {
    return text.replace(/[&<>"']/g, function (m) {
      return ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
      })[m];
    });
  }
}

// Instantiate and expose for inline onclick handlers
document.addEventListener('DOMContentLoaded', () => {
        window.addEventListener("beforeunload", function (e) {
            e.preventDefault();
            e.returnValue = '';
        });
        window.adminPanel = new AdminPanel();
});