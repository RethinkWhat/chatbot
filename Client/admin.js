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
    this.menuData = {};//edits that is applied on DB
    this.draftMenuData = {};//edits yet to be saved
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
    document.getElementById('resetBtn').addEventListener('click', (e) => {
      const btn = e.currentTarget;
      if (btn.disabled) return;
      this.showResetConfirmation();
    });
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

                if (res.status === 401) {
                  this.showStatus("Invalid username or password.", 'error');
                } else if (!res.ok) {
                  this.showStatus("Server error occurred.", 'error');
                } else {
                  sessionStorage.setItem('slu_admin_auth', 'true');
                  this.showAdminPanel();
                  this.showStatus('Login successful!', 'success');
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
            this.markAsSaved();
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
      this.draftMenuData = JSON.parse(JSON.stringify(this.menuData)); // clone for staging
      this.renderMenuList();
      this.markAsSaved();
      console.log("[ADMIN] Menu loaded and saved state reset.");
    } catch (error) {
      console.error("[ADMIN] Failed to fetch menu items:", error);
      this.menuData = {};
      this.draftMenuData = {};
    }
  }

  renderMenuList() {
    this.menuList.innerHTML = '';

    if (!this.draftMenuData || Object.keys(this.draftMenuData).length === 0) {
      this.menuList.innerHTML = '<p>No menu items found.</p>';
      return;
    }

    Object.entries(this.draftMenuData).forEach(([id, draftItem]) => {
      const savedItem = this.menuData[id];
      const isNew = draftItem.isNew;
      const isEdited = !isNew && savedItem && (
        draftItem.title !== savedItem.title ||
        draftItem.emoji !== savedItem.emoji ||
        draftItem.content !== savedItem.content
      );
      const isDeleted = draftItem.isDeleted;

      const menuItem = document.createElement('div');
      menuItem.className = 'menu-item';

      if (isNew) menuItem.classList.add('new');
      if (isEdited) menuItem.classList.add('edited');
      if (isDeleted) menuItem.classList.add('deleted');

      menuItem.innerHTML = `
        <div class="menu-item-header">
          <div class="menu-item-title">
            <span class="emoji">${draftItem.emoji}</span>
            <h3>${this.escapeHtml(draftItem.title)}</h3>
            ${isNew ? '<span class="tag new-tag">New</span>' : ''}
            ${isEdited ? '<span class="tag edited-tag">Edited</span>' : ''}
            ${isDeleted ? '<span class="tag deleted-tag">To Delete</span>' : ''}
          </div>
          <div class="menu-item-actions">
            ${isDeleted
              ? `<button class="action-btn restore" onclick="adminPanel.undoDeleteItem('${id}')">↩️ Undo</button>`
              : `<button class="action-btn edit" onclick="adminPanel.editMenuItem('${id}')">✏️ Edit</button>
                <button class="action-btn delete" onclick="adminPanel.deleteMenuItem('${id}')">🗑️ Delete</button>`}
          </div>
        </div>
        <div class="menu-item-content">${this.formatContentPreview(draftItem.content)}</div>
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
    const item = this.draftMenuData[id];
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
      // Editing existing item in draft (not menuData!)
      this.draftMenuData[this.currentEditingId] = {
        ...this.draftMenuData[this.currentEditingId], // preserve existing flags like isDeleted
        ...menuItem
      };
      console.log(`[ADMIN] Staged edit for item ${this.currentEditingId}:`, this.draftMenuData[this.currentEditingId]);
    } else {
      // Adding a new item to draft
      const newId = this.generateNewId();
      menuItem.isNew = true;
      this.draftMenuData[newId] = menuItem;
      console.log(`[ADMIN] Staged new item ${newId}:`, menuItem);
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
    const item = this.draftMenuData[id];
    if (!item || item.isDeleted) return; // prevent redundant action

    // Stage as deleted
    this.draftMenuData[id] = {
      ...item,
      isDeleted: true
    };

    this.renderMenuList();
    this.markAsUnsaved();
    this.showStatus(`Marked "${item.title}" for deletion.`, 'info');
  }


  undoDeleteItem(id) {
    const item = this.draftMenuData[id];
    if (!item || !item.isDeleted) return;

    // Unmark as deleted
    delete item.isDeleted;

    this.renderMenuList();
    this.markAsUnsaved();
    this.showStatus(`Restored "${item.title}".`, 'success');
  }



  async executeConfirmedAction() {
    if (this.pendingAction === 'delete' && this.pendingDeleteId) {
      this.confirmWindow.classList.remove('active');
      try {
        const res = await fetch(`http://localhost:8000/admin/menu/${this.pendingDeleteId}`, {
          method: "DELETE"
        });
        console.log(`[ADMIN] Deleted item ${this.pendingDeleteId}:`, await res.json());
      } catch (err) {
        console.error(`[ADMIN] Failed to delete item ${this.pendingDeleteId}`, err);
      }
      delete this.draftMenuData[this.pendingDeleteId];
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
    const resetBtn = document.getElementById('resetBtn');
    if (resetBtn.disabled) return; // prevent accidental click
    const isUnsaved = document.getElementById('saveAllBtn').classList.contains('unsaved');

    if (isUnsaved) {
      // Revert local draft (unsaved) changes to last loaded menuData
      this.draftMenuData = JSON.parse(JSON.stringify(this.menuData)); // deep copy
      this.renderMenuList();
      this.showStatus('Reverted to last saved state.', 'info');
      this.markAsSaved();
    } else {
      // Only if no unsaved changes, trigger full reset
      this.pendingAction = 'reset';
      this.showConfirmWindow('Are you sure you want to reset all menu items to default? This cannot be undone.');
    }
  }


  async saveAllChanges() {
    try {
      const entries = Object.entries(this.draftMenuData);

      for (const [id, item] of entries) {
        if (item.isDeleted) {
          if (!item.isNew) {
            // Existing item marked for deletion
            await fetch(`http://localhost:8000/admin/menu/${id}`, {
              method: "DELETE"
            });
            console.log(`[ADMIN] Deleted item ${id}`);
          }
          continue; // Skip to next
        }

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

      // Reload saved state into both data objects
      await this.loadMenuData();
      this.draftMenuData = JSON.parse(JSON.stringify(this.menuData));
      this.renderMenuList();

    } catch (error) {
      console.error("[ADMIN] Save error:", error);
      this.showStatus('Error saving changes to backend.', 'error');
    }
  }

  
  markAsUnsaved() {
    const saveBtn = document.getElementById('saveAllBtn');
    const resetBtn = document.getElementById('resetBtn');

    saveBtn.textContent = '💾 Apply All Changes*';
    saveBtn.classList.add('unsaved', 'blinking');
    saveBtn.disabled = false;
    saveBtn.style.opacity = 1.0;

    resetBtn.disabled = false;
    resetBtn.style.opacity = 1.0;
  }

  markAsSaved() {
    const saveBtn = document.getElementById('saveAllBtn');
    const resetBtn = document.getElementById('resetBtn');

    saveBtn.textContent = '💾 No changes made yet';
    saveBtn.classList.remove('unsaved', 'blinking');
    saveBtn.disabled = true;
    saveBtn.style.opacity = 0.1;

    resetBtn.disabled = true;
    resetBtn.style.opacity = 0.1;
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