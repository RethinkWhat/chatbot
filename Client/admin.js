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

    //scraper popup window items
    this.loadUrlsBtn = document.getElementById('loadUrlsBtn');
    this.saveUrlsBtn = document.getElementById('saveUrlsBtn');
    this.jsonConvertBtn = document.getElementById('jsonConvertBtn');
    this.weaviateBtn = document.getElementById('weaviateBtn');
    this.scrapeBtn = document.getElementById('scrapeBtn');
    
    this.runBtn = document.getElementById('run');
    this.adminCredsBtn = document.getElementById('adminCredsBtn');
    this.userDataBtn = document.getElementById("userDataBtn");
    window.jsonifyFile = jsonifyFile;

  
    
    //file manager popup window items
    // Track selected file globally
    let selectedFile = null;

    // Get DOM references
    this.loadDataFilesBtn = document.getElementById("loadDataFilesBtn");
    this.loadFileListBtn = document.getElementById("loadFileListBtn");
    this.fileTypeSelect = document.getElementById("fileTypeSelect") || document.getElementById("dataType");
    this.userFileList = document.getElementById("userFileList");
    this.userFilename = document.getElementById("userFilename");
    this.userFileEditor = document.getElementById("userFileEditor");
    this.editUserFileBtn = document.getElementById("editUserFileBtn");
    this.saveUserFileBtn = document.getElementById("saveUserFileBtn");
    this.deleteUserFileBtn = document.getElementById("deleteUserFileBtn");
    this.userEditStatus = document.getElementById("userEditStatus");



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
    document.getElementById("weaviateBtn").addEventListener("click", weaviate);
    document.getElementById('resetBtn').addEventListener('click', (e) => {
      const btn = e.currentTarget;
      if (btn.disabled) return;
      this.showResetConfirmation();
    });
    document.getElementById('logoutBtn').addEventListener('click', () => this.logout());
    document.getElementById("closeScrapeWindow").addEventListener("click", () => {
      document.getElementById("scrapeWindow").classList.remove("active");
    });
    document.getElementById("closeAdminCredsWindow").addEventListener("click", (e) => {
      document.getElementById("adminCredsWindow").classList.remove("active");
    })

    
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

  
  async checkAuthentication() {
    const isAuthenticated = sessionStorage.getItem('slu_admin_auth') === 'true';
    if (!isAuthenticated) return;

    try {
      const res = await fetch("http://localhost:8000/admin/ping");
      if (res.ok) {
        this.showAdminPanel();
      } else {
        throw new Error("Session invalid");
      }
    } catch {
      sessionStorage.removeItem('slu_admin_auth');
      this.loginSection.style.display = 'flex';
      this.adminContent.style.display = 'none';
      this.showStatus("Session expired. Please log in again.", 'error');
    }
  }

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
    const allIds = [...Object.keys(this.menuData), ...Object.keys(this.draftMenuData)];
    const numericIds = allIds.map(id => parseInt(id)).filter(n => !isNaN(n));
    return (Math.max(...numericIds, 0) + 1).toString();
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
    const saveBtn = document.getElementById('saveAllBtn');
    saveBtn.disabled = true;
    try {
      const entries = Object.entries(this.draftMenuData);

      for (const [id, item] of entries) {
        if (item.isDeleted) {
          if (!item.isNew) {
            await fetch(`http://localhost:8000/admin/menu/${id}`, { method: "DELETE" });
            console.log(`[ADMIN] Deleted item ${id}`);
          }
          continue;
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

      await this.loadMenuData();
      this.draftMenuData = JSON.parse(JSON.stringify(this.menuData));
      this.renderMenuList();

    } catch (error) {
      console.error("[ADMIN] Save error:", error);
      this.showStatus('Error saving changes to backend.', 'error');
    } finally {
      saveBtn.disabled = false;
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
  //pagination for JSONification page
  let allJsonFiles = [];
  let filteredJsonFiles = [];
  let currentJsonPage = 1;
  const filesPerJsonPage = 10;

// Instantiate and expose for inline onclick handlers
document.addEventListener('DOMContentLoaded', () => {
        window.addEventListener("beforeunload", function (e) {
            e.preventDefault();
            e.returnValue = '';
        });
        window.adminPanel = new AdminPanel();
});

// Load URLs into textarea on popup open
document.getElementById("scrapeBtn").addEventListener("click", async () => {
  document.getElementById("scrapeWindow").classList.add("active");

  try {
    const res = await fetch("http://localhost:8000/scrape/urls");
    const data = await res.json();
    document.getElementById("urlsEditor").value = data.urls.join("\n");
  } catch (err) {
    console.error("Failed to load urls.txt:", err);
  }
});



document.getElementById("closeScrapeWindow").addEventListener("click", () => {
  document.getElementById("scrapeWindow").classList.remove("active");
});

//open admin creds window
document.getElementById("adminCredsBtn").addEventListener("click", async () => {
  document.getElementById("adminCredsWindow").classList.add("active");
});


// add even listener for the btns inside scrap window popup:
document.getElementById("webScrapeBtn").addEventListener("click", () => {
  document.getElementById("webScrapeWindow").style.display = "flex";
  document.getElementById("webScrapeBtn").classList.add("slowBlinking");
  document.getElementById("uploadWindow").style.display = "none";
  document.getElementById("fileUploadBtn").classList.remove("slowBlinking");
  document.getElementById("donutWindow").style.display = "none";
  document.getElementById("donutCtrlBtn").classList.remove("slowBlinking");
  document.getElementById("userDataWindow").style.display = "none";
  document.getElementById("userDataBtn").classList.remove("slowBlinking");
});

document.getElementById("fileUploadBtn").addEventListener("click", () => {
  document.getElementById("webScrapeWindow").style.display = "none";
  document.getElementById("webScrapeBtn").classList.remove("slowBlinking");
  document.getElementById("uploadWindow").style.display = "flex";
  document.getElementById("fileUploadBtn").classList.add("slowBlinking");
  document.getElementById("donutWindow").style.display = "none";
  document.getElementById("donutCtrlBtn").classList.remove("slowBlinking");
  document.getElementById("userDataWindow").style.display = "none";
  document.getElementById("userDataBtn").classList.remove("slowBlinking");
});

document.getElementById("donutCtrlBtn").addEventListener("click", () => {
  document.getElementById("webScrapeWindow").style.display = "none";
  document.getElementById("webScrapeBtn").classList.remove("slowBlinking");
  document.getElementById("uploadWindow").style.display = "none";
  document.getElementById("fileUploadBtn").classList.remove("slowBlinking");
  document.getElementById("donutWindow").style.display = "flex";
  document.getElementById("donutCtrlBtn").classList.add("slowBlinking");
  document.getElementById("userDataWindow").style.display = "none";
  document.getElementById("userDataBtn").classList.remove("slowBlinking");
});

document.getElementById("userDataBtn").addEventListener("click", () => {
  document.getElementById("webScrapeWindow").style.display = "none";
  document.getElementById("webScrapeBtn").classList.remove("slowBlinking");
  document.getElementById("uploadWindow").style.display = "none";
  document.getElementById("fileUploadBtn").classList.remove("slowBlinking");
  document.getElementById("donutWindow").style.display = "none";
  document.getElementById("donutCtrlBtn").classList.remove("slowBlinking");
  document.getElementById("userDataWindow").style.display = "flex";
  document.getElementById("userDataBtn").classList.add("slowBlinking");
});


//web scraper triggered, shows logger (run scrapper when form is submitted)
document.getElementById("scrapeForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const depth = document.getElementById("depth").value;
  const output = document.getElementById("scrapeOutput");
  output.textContent = "⏳ Starting scraper...\n";

  const res = await fetch("http://localhost:8000/scrape/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ depth: depth })
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });
    output.textContent += chunk.replace(/^data: /gm, "").trim() + "\n";
    output.scrollTop = output.scrollHeight;
  }
});


//loads url when the load url button is clicked
document.getElementById("loadUrlsBtn").addEventListener("click", async () => {
  const output = document.getElementById("urlsStatus");
  output.textContent = "⏳ Loading URLs...";
  try {
    const res = await fetch("http://localhost:8000/urls");
    const data = await res.json();
    document.getElementById("urlsEditor").value = data.urls.join("\n");
    output.textContent = "✅ URLs loaded.";
  } catch (err) {
    output.textContent = "❌ Failed to load URLs.";
    console.error(err);
  }
});
// Save updated content to urls.txt
document.getElementById("saveUrlsBtn").addEventListener("click", async () => {
  const output = document.getElementById("urlsStatus");
  const content = document.getElementById("urlsEditor").value
    .split("\n")
    .map(line => line.trim())
    .filter(line => line.length > 0); // Remove empty lines

  output.textContent = "⏳ Saving URLs...";
  try {
    const res = await fetch("http://localhost:8000/urls", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ urls: content })
    });
    const data = await res.json();
    output.textContent = "✅ " + data.status;
  } catch (err) {
    output.textContent = "❌ Failed to save URLs.";
    console.error(err);
  }
});

//receive uploaded form
document.getElementById("uploadForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("uploadInput");
  const formData = new FormData();
  for (const file of input.files) {
    formData.append("files", file);
  }
  const res = await fetch("http://localhost:8000/upload", {
    method: "POST",
    body: formData
  });
  const data = await res.json();
  document.getElementById("uploadOutput").textContent = JSON.stringify(data.uploaded, null, 2);

  //also call pdf/img -> txt
  const output = document.getElementById("uploadOutput");
      output.textContent = "⏳ Scanning PDFs...";
      try {
        const res = await fetch("http://localhost:8000/trigger/pdf", {
          method: "POST"
        });
        const data = await res.json();
        output.textContent = "✅ " + data.status;
      } catch (err) {
        output.textContent = "❌ Failed to scan PDFs.";
        console.error(err);
      }
    
      try{
        const res = await fetch("http://localhost:8000/trigger/image", {
          method: "POST"
        });
        const data = await res.json();
        output.textContent += "\n✅ " + data.status;
      } catch (err) {
        output.textContent += "\n❌ Failed to scan images.";
        console.error(err);
      }
});


//display JSONification progress
document.getElementById("jsonConvertBtn").addEventListener("click", () => {
  const output = document.getElementById("JSONifyOutput");
  output.textContent = "Starting JSONification...\n";

  const eventSource = new EventSource("http://localhost:8500/batch-txt2json");

  eventSource.onmessage = function (event) {
      output.textContent += event.data + "\n";
      output.scrollTop = output.scrollHeight;  // Auto-scroll
  };

  eventSource.onerror = function (err) {
      output.textContent += "\n[ERROR] Connection lost or server error.\n";
      eventSource.close();
  };
});

//single JSONification
async function jsonifyFile(filename) {
  if (!filename) {
    showUserMessage("❌ No file selected for JSONification", true);
    return;
  }

  const statusBox = document.getElementById("editStatus");
  statusBox.textContent = `🔄 Sending ${filename} to JSONifier...`;

  try {
    const res = await fetch(`http://localhost:8500/txt2json?file=${encodeURIComponent(filename)}`, {
      method: "POST",
    });

    const data = await res.json();

    if (!res.ok) {
      statusBox.textContent = `❌ ${data.error || "Unknown error"}`;
      return;
    }

    statusBox.textContent = data.status || "✅ JSONification completed.";
  } catch (err) {
    statusBox.textContent = `❌ Request failed: ${err.message}`;
  }
}

//weaviate 
async function weaviate() {
  const output = document.getElementById("JSONifyOutput");
  output.textContent = "📡 Uploading to Weaviate...";

  try {
    const res = await fetch("http://localhost:8000/weaviate/upload", {
      method: "POST"
    });

    const data = await res.json();

    if (res.ok) {
      output.innerHTML =
        `✅ Weaviation complete!\n` +
        `Files processed: ${data.files_processed}\n\n` +
        `Preview:\n${data.sample.map(entry => `• ${entry.title}`).join("\n")}`;
    } else {
      output.textContent = `❌ Upload failed: ${data.error || JSON.stringify(data)}`;
    }
  } catch (err) {
    output.textContent = `❌ Error connecting to backend: ${err.message}`;
  }
}




//admin Creds Form
document.getElementById("adminCredsForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const username = document.getElementById("newUsername").value.trim();
  const password = document.getElementById("newPassword").value.trim();
  const confirm = document.getElementById("confirmPassword").value.trim();
  const statusBox = document.getElementById("credsStatus");

  if (!username || !password || !confirm) {
    statusBox.textContent = "❌ All fields are required.";
    return;
  }

  if (password !== confirm) {
    statusBox.textContent = "❌ Passwords do not match.";
    return;
  }

  try {
    const res = await fetch("http://localhost:8000/api/admin/update-credentials", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ newUsername: username, newPassword: password })
    });

    const data = await res.json();
    if (!res.ok) {
      statusBox.textContent = `❌ ${data.detail || "Unknown error"}`;
    } else {
      statusBox.textContent = data.message || "✅ Credentials updated.";
      document.getElementById("adminCredsForm").reset();
      statusBox.classList.add("flash");
      setTimeout(() => statusBox.classList.remove("flash"), 1000);

    }
  } catch (err) {
    statusBox.textContent = `❌ Request failed: ${err.message}`;
  }
});


// PREVIEW,EDIT and DELETE function
// Constants for pagination
let selectedFile = "";
let currentPage = 1;
let filesPerPage = 10;
let currentFileType = "txt";
let fullFileList = [];
let filteredFileList = [];  // Subset of fullFileList matching search


// Load files button
document.getElementById("loadDataFilesBtn").addEventListener("click", async () => {
  currentFileType = document.getElementById("dataType").value || "txt";
  currentPage = 1;
  await fetchFiles();
});

async function fetchFiles() {
  try {
    const res = await fetch(`http://localhost:8000/api/files?type=${currentFileType}`);
    const { files } = await res.json();
    fullFileList = files;
    displayPaginatedFiles();
  } catch (err) {
    userEditStatus.textContent = `❌ Failed to load files: ${err}`;
  }
}

function displayPaginatedFiles(type = "txt") {
  const startIdx = (currentPage - 1) * filesPerPage;
  const endIdx = startIdx + filesPerPage;
  const currentFiles = filteredFileList.slice(startIdx, endIdx);

  const fileListEl = document.getElementById('userFileList');
  fileListEl.innerHTML = '';

  currentFiles.forEach(filename => {
    const li = document.createElement('li');
    li.textContent = filename;

    // Preview Button
    const previewBtn = document.createElement('button');
    previewBtn.textContent = '👁 Preview';
    previewBtn.onclick = () => previewFile(filename, type);

    // Edit Button
    const editBtn = document.createElement('button');
    editBtn.textContent = '✏️ Edit';
    editBtn.onclick = () => openEditorModal(filename, type);

    // Delete Button
    const deleteBtn = document.createElement('button');
    deleteBtn.textContent = '🗑 Delete';
    deleteBtn.onclick = () => deleteFile(filename, type);

    li.append(previewBtn, editBtn, deleteBtn);
    fileListEl.appendChild(li);
  });

  updatePageIndicator();
}


function updatePageIndicator() {
  const pageCount = Math.ceil(filteredFileList.length / filesPerPage);
  document.getElementById('pageIndicator').textContent = `Page ${currentPage} of ${pageCount}`;

  document.getElementById('prevPageBtn').disabled = currentPage === 1;
  document.getElementById('nextPageBtn').disabled = currentPage === pageCount || pageCount === 0;
}

document.getElementById('prevPageBtn').onclick = () => {
  if (currentPage > 1) {
    currentPage--;
    displayPaginatedFiles();
  }
};

document.getElementById('nextPageBtn').onclick = () => {
  const pageCount = Math.ceil(fullFileList.length / filesPerPage);
  if (currentPage < pageCount) {
    currentPage++;
    displayPaginatedFiles();
  }
};

async function loadUserFiles() {
  const fileType = document.getElementById('dataType').value || "txt";
  const res = await fetch(`http://localhost:8000/api/files?type=${fileType}`);
  const data = await res.json();

  fullFileList = data.files || [];
  filteredFileList = [...fullFileList];
  currentPage = 1;
  displayPaginatedFiles(fileType);  // Pass fileType here
}




//user enters text in searchbar
document.getElementById("userFileSearch").addEventListener("input", () => {
  const query = document.getElementById("userFileSearch").value.toLowerCase().trim();
  filteredFileList = fullFileList.filter(name => name.toLowerCase().includes(query));
  currentPage = 1;
  displayPaginatedFiles();
});



document.getElementById('loadDataFilesBtn').onclick = loadUserFiles;



function renderFileList(files) {
  const list = document.getElementById("userFileList");
  list.innerHTML = "";
  files.forEach((name) => {
    const li = document.createElement("li");
    li.innerHTML = `
      ${name}
      <button onclick="previewFile('${name}', '${currentFileType}')">👁️ Preview</button>
      <button onclick="openEditorModal('${name}', '${currentFileType}')">📝 Edit</button>
      <button onclick="deleteFile('${name}', '${currentFileType}')">🗑️ Delete</button>
    `;
    list.appendChild(li);
  });
}

function renderPaginationControls() {
  const totalPages = Math.ceil(fullFileList.length / filesPerPage);
  const controls = document.getElementById("paginationControls") || document.createElement("div");
  controls.id = "paginationControls";
  controls.innerHTML = "";

  for (let i = 1; i <= totalPages; i++) {
    const btn = document.createElement("button");
    btn.classList.add("toolbar-btn");
    btn.textContent = i;
    btn.disabled = i === currentPage;
    btn.onclick = () => {
      currentPage = i;
      displayPaginatedFiles();
    };
    controls.appendChild(btn);
  }

  // Attach below the file list
  document.getElementById("userFileList").after(controls);
}

// Search functionality
document.getElementById("searchInput").addEventListener("input", () => {
  const query = document.getElementById("searchInput").value.toLowerCase().trim();
  filteredJsonFiles = allJsonFiles.filter(name => name.toLowerCase().includes(query));
  currentJsonPage = 1;
  displayJsonifierFiles();
});


// Preview
async function previewFile(name, type) {
  selectedFile = name;
  userFilename.textContent = name;
  try {
    const res = await fetch(`http://localhost:8000/api/file?type=${type}&name=${name}`);
    const { content } = await res.json();
    userFileEditor.value = content;
    userFileEditor.style.display = "block";
    saveUserFileBtn.style.display = "none";
  } catch (err) {
    userEditStatus.textContent = `❌ Failed to load content: ${err}`;
  }
}

// Edit
async function openEditorModal(name, type = "txt") {
  selectedFile = name;
  userFilename.textContent = name;
  try {
    const res = await fetch(`http://localhost:8000/api/file?type=${type}&name=${name}`);
    const { content } = await res.json();
    userFileEditor.value = content;
    userFileEditor.style.display = "block";
    saveUserFileBtn.style.display = "inline-block";
  } catch (err) {
    userEditStatus.textContent = `❌ Error: ${err}`;
  }
}

// Save
document.getElementById("saveUserFileBtn").addEventListener("click", saveEditedFile);

async function saveEditedFile() {
  const content = userFileEditor.value;
  const type = document.getElementById("dataType").value || "txt";
  try {
    const res = await fetch(`http://localhost:8000/api/file/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: selectedFile, type, content }),
    });
    const result = await res.json();
    userFileEditor.style.display = "none";
    showUserMessage("✅ File saved and editor closed.");
    saveUserFileBtn.style.display = "none";
  } catch (err) {
    userEditStatus.textContent = `❌ Save failed: ${err}`;
  }
}

// Delete
async function deleteFile(name, type = "txt") {
  if (!confirm(`Delete ${name}?`)) return;
  try {
    const res = await fetch(`http://localhost:8000/api/file?type=${type}&name=${name}`, {
      method: "DELETE",
    });
    const result = await res.json();
    userFileEditor.style.display = "none";
    showUserMessage("🗑️ File deleted and editor closed.");

    fetchFiles();
  } catch (err) {
    userEditStatus.textContent = `❌ Deletion failed: ${err}`;
  }
}

// Close editor
function closeEditorModal() {
  userFileEditor.style.display = "none";
  userEditStatus.textContent = "";
}

//animation: Edit status
function showUserMessage(message, isError = false) {
  const el = document.getElementById("userEditStatus");
  el.textContent = message;
  el.classList.remove("blink");
  el.style.color = isError ? "red" : "green";
  void el.offsetWidth; // Trigger reflow to restart animation
  el.classList.add("blink");
}


// ==================FILE JSONIFICATION
// document.getElementById("loadFileListBtn").addEventListener("click", async () => {
//   const res = await fetch("http://localhost:8000/list-txt-files");
//   const { files } = await res.json();

//   const searchInput = document.getElementById("searchInput").value.trim().toLowerCase();

//   // Default behavior: if search is empty, show all
//   const filtered = searchInput
//     ? files.filter(name => name.toLowerCase().includes(searchInput))
//     : files;

//   currentPage = 1; // reset pagination
//   displayFileList(filtered);
// });
document.getElementById("loadFileListBtn").addEventListener("click", () => {
  loadJsonifierFileList();
  document.getElementById("donutWindow").style.display = "block";
});



//user clicks load files btn
document.getElementById("searchInput").addEventListener("input", () => {
  const query = document.getElementById("searchInput").value.toLowerCase().trim();
  filteredJsonFiles = allJsonFiles.filter(name => name.toLowerCase().includes(query));
  currentJsonPage = 1;
  displayJsonifierFiles();
});

async function loadJsonifierFileList() {
  try {
    const res = await fetch('http://localhost:8000/api/files?type=txt');
    const data = await res.json();
    allJsonFiles = data.files || [];
    filteredJsonFiles = [...allJsonFiles];
    currentJsonPage = 1;
    displayJsonifierFiles();
  } catch (err) {
    console.error("Failed to load files:", err);
  }
}




async function fetchJsonifierFiles() {
  try {
    const res = await fetch("http://localhost:8000/api/files?type=txt");
    const data = await res.json();
    allJsonFiles = data.files || [];
    filteredJsonFiles = [...allJsonFiles];
    currentJsonPage = 1;
    displayJsonifierFiles();
  } catch (err) {
    document.getElementById('fileList').innerHTML = `<li>❌ Error loading files: ${err}</li>`;
  }
}

function displayJsonifierFiles() {
  const startIdx = (currentJsonPage - 1) * filesPerJsonPage;
  const endIdx = startIdx + filesPerJsonPage;
  const currentFiles = filteredJsonFiles.slice(startIdx, endIdx);

  const fileListEl = document.getElementById('fileList');
  fileListEl.innerHTML = '';

  currentFiles.forEach(file => {
    const li = document.createElement('li');
    li.textContent = file;
    li.style.cursor = "pointer";
    li.onclick = () => {
      selectedFile = file;
      document.querySelectorAll('#fileList li').forEach(el => el.style.background = '');
      li.style.background = '#ddd';
      previewJsonFile(file);
    };
    fileListEl.appendChild(li);
  });

  renderJsonPaginationControls();
}



function renderJsonPaginationControls() {
  let controls = document.getElementById('jsonPaginationControls');
  if (!controls) {
    controls = document.createElement('div');
    controls.id = 'jsonPaginationControls';
    controls.style.marginTop = "10px";
    controls.style.display = "flex";
    controls.style.gap = "10px";
    document.getElementById('fileListContainer').appendChild(controls);
  }

  const totalPages = Math.max(1, Math.ceil(filteredJsonFiles.length / filesPerJsonPage));
  controls.innerHTML = '';

  const prevBtn = document.createElement('button');
  prevBtn.textContent = '⬅️ Prev';
  prevBtn.className = 'toolbar-btn';
  prevBtn.disabled = currentJsonPage === 1;
  prevBtn.onclick = () => {
    if (currentJsonPage > 1) {
      currentJsonPage--;
      displayJsonifierFiles();
    }
  };
  controls.appendChild(prevBtn);

  const pageIndicator = document.createElement('span');
  pageIndicator.textContent = `Page ${currentJsonPage} of ${totalPages}`;
  controls.appendChild(pageIndicator);

  const nextBtn = document.createElement('button');
  nextBtn.textContent = '➡️ Next';
  nextBtn.className = 'toolbar-btn';
  nextBtn.disabled = currentJsonPage === totalPages;
  nextBtn.onclick = () => {
    if (currentJsonPage < totalPages) {
      currentJsonPage++;
      displayJsonifierFiles();
    }
  };
  controls.appendChild(nextBtn);
}

async function previewJsonFile(name) {
  const previewEl = document.getElementById('filePreview');
  previewEl.textContent = "Loading preview...";
  try {
    const res = await fetch(`http://localhost:8000/api/file?type=txt&name=${name}`);
    const { content } = await res.json();
    previewEl.textContent = content;
  } catch (err) {
    previewEl.textContent = `❌ Failed to load file content: ${err}`;
  }
}

// Initial load (when popup opens)
document.getElementById("donutWindow").addEventListener("show", fetchJsonifierFiles);
