/**
 * AI RESEARCH PULSE - FRONTEND APPLICATION LOGIC
 * vanilla JavaScript (ES6)
 */

// 1. APPLICATION STATE
const state = {
    articles: [],
    filteredArticles: [],
    categories: [],
    sources: [],
    
    // Filters & Sorting
    searchQuery: '',
    activeCategory: 'all',
    activeSource: 'all',
    activeSort: 'latest',
    
    // Copilot State
    selectedArticle: null,
    selectedTone: 'professional',
    selectedFormat: 'linkedin',
    isGenerating: false,
    
    // UI Helpers
    searchDebounceTimer: null
};

// 2. DOM ELEMENTS
const DOM = {
    // Header
    articleCount: document.getElementById('articleCount'),
    lastUpdatedTime: document.getElementById('lastUpdatedTime'),
    refreshBtn: document.getElementById('refreshBtn'),
    refreshIcon: document.getElementById('refreshIcon'),
    
    // Controls
    searchInput: document.getElementById('searchInput'),
    clearSearchBtn: document.getElementById('clearSearchBtn'),
    sourceSelect: document.getElementById('sourceSelect'),
    sortSelect: document.getElementById('sortSelect'),
    categoryPillsWrapper: document.getElementById('categoryPillsWrapper'),
    resetFiltersBtn: document.getElementById('resetFiltersBtn'),
    noResultsState: document.getElementById('noResultsState'),
    
    // Dashboard Cards Grid
    cardsGrid: document.getElementById('cardsGrid'),
    
    // Drawer & Overlay
    drawerOverlay: document.getElementById('drawerOverlay'),
    copilotDrawer: document.getElementById('copilotDrawer'),
    closeDrawerBtn: document.getElementById('closeDrawerBtn'),
    
    // Drawer Content Display
    drawerSource: document.getElementById('drawerSource'),
    drawerCategory: document.getElementById('drawerCategory'),
    drawerTitle: document.getElementById('drawerTitle'),
    drawerAuthors: document.getElementById('drawerAuthors'),
    drawerDate: document.getElementById('drawerDate'),
    drawerAbstract: document.getElementById('drawerAbstract'),
    drawerOriginalLink: document.getElementById('drawerOriginalLink'),
    
    // Copilot Generation Controls
    toneGrid: document.getElementById('toneGrid'),
    formatGrid: document.getElementById('formatGrid'),
    generateBtn: document.getElementById('generateBtn'),
    
    // Copilot Output
    outputContainer: document.getElementById('outputContainer'),
    outputTextArea: document.getElementById('outputTextArea'),
    copyBtn: document.getElementById('copyBtn'),
    downloadBtn: document.getElementById('downloadBtn'),
    generationLoader: document.getElementById('generationLoader')
};

// 3. INITIALIZATION & ROUTING
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    fetchUpdates(false); // Initial load (without force refresh)
});

// 4. EVENT LISTENERS SETUP
function initEventListeners() {
    // Fetch / Sync feeds
    DOM.refreshBtn.addEventListener('click', () => fetchUpdates(true));
    
    // Real-time Search with Debouncing
    DOM.searchInput.addEventListener('input', (e) => {
        state.searchQuery = e.target.value.trim();
        toggleClearSearchButton();
        
        clearTimeout(state.searchDebounceTimer);
        state.searchDebounceTimer = setTimeout(() => {
            applyFiltersAndSorting();
        }, 250); // 250ms debounce
    });
    
    DOM.clearSearchBtn.addEventListener('click', () => {
        DOM.searchInput.value = '';
        state.searchQuery = '';
        toggleClearSearchButton();
        applyFiltersAndSorting();
        DOM.searchInput.focus();
    });
    
    // Filter & Sort Dropdowns
    DOM.sourceSelect.addEventListener('change', (e) => {
        state.activeSource = e.target.value;
        applyFiltersAndSorting();
    });
    
    DOM.sortSelect.addEventListener('change', (e) => {
        state.activeSort = e.target.value;
        applyFiltersAndSorting();
    });
    
    // Reset Filters Button
    DOM.resetFiltersBtn.addEventListener('click', resetAllFilters);
    
    // Category pills event delegation
    DOM.categoryPillsWrapper.addEventListener('click', (e) => {
        const pill = e.target.closest('.category-pill');
        if (!pill) return;
        
        // Update active class
        document.querySelectorAll('.category-pill').forEach(btn => btn.classList.remove('active'));
        pill.classList.add('active');
        
        // Filter category
        state.activeCategory = pill.dataset.category;
        applyFiltersAndSorting();
        
        // Scroll active pill into view smoothly if overflowed
        pill.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
    });
    
    // Drawer Overlay & Close
    DOM.drawerOverlay.addEventListener('click', closeCopilotDrawer);
    DOM.closeDrawerBtn.addEventListener('click', closeCopilotDrawer);
    
    // Copilot Tone option cards selector
    DOM.toneGrid.addEventListener('click', (e) => {
        const toneCard = e.target.closest('.option-card');
        if (!toneCard) return;
        
        DOM.toneGrid.querySelectorAll('.option-card').forEach(btn => btn.classList.remove('active'));
        toneCard.classList.add('active');
        state.selectedTone = toneCard.dataset.tone;
    });
    
    // Copilot Format option cards selector
    DOM.formatGrid.addEventListener('click', (e) => {
        const formatCard = e.target.closest('.option-card');
        if (!formatCard) return;
        
        DOM.formatGrid.querySelectorAll('.option-card').forEach(btn => btn.classList.remove('active'));
        formatCard.classList.add('active');
        state.selectedFormat = formatCard.dataset.format;
    });
    
    // Generate Button Click
    DOM.generateBtn.addEventListener('click', generateCopilotOutput);
    
    // Clipboard Copy Action
    DOM.copyBtn.addEventListener('click', copyToClipboard);
    
    // Download Action
    DOM.downloadBtn.addEventListener('click', downloadOutputAsText);

    // Drawer Tabs switching
    const tabBtnDetails = document.getElementById('tabBtnDetails');
    const tabBtnGenerator = document.getElementById('tabBtnGenerator');
    if (tabBtnDetails && tabBtnGenerator) {
        tabBtnDetails.addEventListener('click', () => switchDrawerTab('details'));
        tabBtnGenerator.addEventListener('click', () => switchDrawerTab('generator'));
    }
}

// 5. FETCH & DATA PIPELINE
async function fetchUpdates(forceRefresh = false) {
    showLoadingState();
    
    const endpoint = forceRefresh ? '/api/refresh' : '/api/updates';
    
    try {
        const response = await fetch(endpoint);
        const data = await response.json();
        
        if (data.success) {
            state.articles = data.items;
            state.categories = data.categories;
            state.sources = data.sources;
            
            // Update last updated metadata
            DOM.articleCount.textContent = state.articles.length;
            if (data.last_updated) {
                // Formatting time for friendly UI view
                DOM.lastUpdatedTime.textContent = formatTimestamp(data.last_updated);
            }
            
            // Build / update drop down options dynamically (if not already populated)
            populateFilterOptions();
            
            // Apply current filters to fresh state
            applyFiltersAndSorting();
        } else {
            console.error('Failed to sync feeds:', data.error);
            showErrorMessage('Error syncing research feeds. Please try again.');
        }
    } catch (error) {
        console.error('Network error during fetch:', error);
        showErrorMessage('A network error occurred. Please check your connection.');
    } finally {
        hideLoadingState();
    }
}

// 6. FILTERING & SORTING LOGIC (Instant Client-Side)
function applyFiltersAndSorting() {
    let results = [...state.articles];
    
    // 1. Text Query Filter
    if (state.searchQuery) {
        const query = state.searchQuery.toLowerCase();
        results = results.filter(item => 
            item.title.toLowerCase().includes(query) || 
            item.summary.toLowerCase().includes(query) || 
            item.authors.toLowerCase().includes(query)
        );
    }
    
    // 2. Topic/Category Pill Filter
    if (state.activeCategory !== 'all') {
        results = results.filter(item => 
            item.category.toLowerCase() === state.activeCategory.toLowerCase()
        );
    }
    
    // 3. Publisher/Source Filter
    if (state.activeSource !== 'all') {
        results = results.filter(item => 
            item.source.toLowerCase() === state.activeSource.toLowerCase()
        );
    }
    
    // 4. Sort Ordering
    if (state.activeSort === 'oldest') {
        results.sort((a, b) => new Date(a.published) - new Date(b.published));
    } else if (state.activeSort === 'az') {
        results.sort((a, b) => a.title.localeCompare(b.title));
    } else { // 'latest'
        results.sort((a, b) => new Date(b.published) - new Date(a.published));
    }
    
    state.filteredArticles = results;
    renderArticlesGrid();
}

function resetAllFilters() {
    DOM.searchInput.value = '';
    state.searchQuery = '';
    toggleClearSearchButton();
    
    state.activeCategory = 'all';
    document.querySelectorAll('.category-pill').forEach(btn => {
        if (btn.dataset.category === 'all') {
            btn.classList.add('active');
            btn.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
        } else {
            btn.classList.remove('active');
        }
    });
    
    state.activeSource = 'all';
    DOM.sourceSelect.value = 'all';
    
    state.activeSort = 'latest';
    DOM.sortSelect.value = 'latest';
    
    applyFiltersAndSorting();
}

// 7. RENDERING SYSTEM
function renderArticlesGrid() {
    DOM.cardsGrid.innerHTML = '';
    
    if (state.filteredArticles.length === 0) {
        DOM.noResultsState.classList.remove('hidden');
        DOM.cardsGrid.classList.add('hidden');
        return;
    }
    
    DOM.noResultsState.classList.add('hidden');
    DOM.cardsGrid.classList.remove('hidden');
    
    const fragment = document.createDocumentFragment();
    
    state.filteredArticles.forEach(item => {
        const card = document.createElement('article');
        card.className = 'card';
        card.dataset.id = item.id;
        card.dataset.source = item.source;
        card.dataset.category = item.category;
        
        card.innerHTML = `
            <div class="card-header-meta">
                <div class="badges-wrapper">
                    <span class="badge badge-source">${item.source}</span>
                    <span class="badge badge-category">${item.category}</span>
                </div>
                <time class="card-date">${item.date_pretty}</time>
            </div>
            <h3 class="card-title" title="${escapeHtml(item.title)}">${item.title}</h3>
            <p class="card-authors" title="${escapeHtml(item.authors)}">By ${item.authors}</p>
            <p class="card-summary">${item.summary}</p>
            <div class="card-footer">
                <a href="${item.link}" target="_blank" class="card-external-link" rel="noopener noreferrer">
                    <span>Source Paper</span>
                    <i class="fa-solid fa-up-right-from-square"></i>
                </a>
                <button class="card-action-btn select-article-btn">
                    <i class="fa-solid fa-wand-magic-sparkles"></i>
                    <span>AI Post & Summary</span>
                </button>
            </div>
        `;
        
        // Add card interaction handlers
        // Click action button opens Copilot directly in generator view
        card.querySelector('.select-article-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            openCopilotDrawer(item, 'generator');
        });
        
        // Clicking card body opens Copilot in abstract details view
        card.addEventListener('click', () => {
            openCopilotDrawer(item, 'details');
        });
        
        fragment.appendChild(card);
    });
    
    DOM.cardsGrid.appendChild(fragment);
}

// 8. LOADING & ERROR STATES
function showLoadingState() {
    DOM.refreshIcon.classList.add('spinning');
    DOM.refreshBtn.disabled = true;
    
    // Display shimmering skeleton cards
    DOM.noResultsState.classList.add('hidden');
    DOM.cardsGrid.classList.remove('hidden');
    DOM.cardsGrid.innerHTML = '';
    
    for (let i = 0; i < 6; i++) {
        const skeleton = document.createElement('div');
        skeleton.className = 'skeleton-card';
        skeleton.innerHTML = `
            <div class="skeleton-meta">
                <div class="skeleton-shimmer skeleton-badge-1"></div>
                <div class="skeleton-shimmer skeleton-badge-2"></div>
                <div class="skeleton-shimmer skeleton-date"></div>
            </div>
            <div class="skeleton-shimmer skeleton-title"></div>
            <div class="skeleton-shimmer skeleton-author"></div>
            <div class="skeleton-shimmer skeleton-text"></div>
            <div class="skeleton-shimmer skeleton-text-short"></div>
            <div class="skeleton-footer">
                <div class="skeleton-shimmer skeleton-link"></div>
                <div class="skeleton-shimmer skeleton-button"></div>
            </div>
        `;
        DOM.cardsGrid.appendChild(skeleton);
    }
}

function hideLoadingState() {
    DOM.refreshIcon.classList.remove('spinning');
    DOM.refreshBtn.disabled = false;
}

function showErrorMessage(message) {
    DOM.cardsGrid.innerHTML = `
        <div class="no-results-state" style="border-color: rgba(239, 68, 68, 0.3);">
            <div class="no-results-icon-wrapper" style="color: #EF4444;">
                <i class="fa-solid fa-triangle-exclamation"></i>
            </div>
            <h3 style="color: #EF4444;">Error Loading Updates</h3>
            <p>${message}</p>
            <button class="btn btn-secondary" onclick="fetchUpdates(true)">Try Syncing Feeds Again</button>
        </div>
    `;
}

// 9. COPILOT SIDE DRAWER CONTROL
function openCopilotDrawer(article, defaultTab = 'details') {
    state.selectedArticle = article;
    
    // Populate article information
    DOM.drawerSource.textContent = article.source;
    DOM.drawerCategory.textContent = article.category;
    DOM.drawerTitle.textContent = article.title;
    DOM.drawerAuthors.textContent = `By ${article.authors}`;
    DOM.drawerDate.textContent = article.date_pretty;
    DOM.drawerAbstract.textContent = article.summary;
    DOM.drawerOriginalLink.href = article.link;
    
    // Reset/clear generator output
    DOM.outputContainer.classList.add('hidden');
    DOM.outputTextArea.value = '';
    
    // Set appropriate active badges in the options grids based on selection
    resetGeneratorButtons();
    
    // Switch to default tab
    switchDrawerTab(defaultTab);
    
    // Show drawer
    DOM.drawerOverlay.classList.add('active');
    DOM.copilotDrawer.classList.add('active');
    
    // Disable background page scrolling
    document.body.style.overflow = 'hidden';
}

function closeCopilotDrawer() {
    DOM.copilotDrawer.classList.remove('active');
    DOM.drawerOverlay.classList.remove('active');
    
    // Re-enable background scrolling
    document.body.style.overflow = '';
}

function switchDrawerTab(tabName) {
    const tabBtnDetails = document.getElementById('tabBtnDetails');
    const tabBtnGenerator = document.getElementById('tabBtnGenerator');
    const detailsPane = document.getElementById('detailsPane');
    const generatorPane = document.getElementById('generatorPane');
    
    if (!tabBtnDetails || !tabBtnGenerator || !detailsPane || !generatorPane) return;
    
    if (tabName === 'details') {
        tabBtnDetails.classList.add('active');
        tabBtnGenerator.classList.remove('active');
        detailsPane.classList.add('active');
        generatorPane.classList.remove('active');
    } else {
        tabBtnDetails.classList.remove('active');
        tabBtnGenerator.classList.add('active');
        detailsPane.classList.remove('active');
        generatorPane.classList.add('active');
    }
}

function resetGeneratorButtons() {
    // Reset Tone Grid
    DOM.toneGrid.querySelectorAll('.option-card').forEach(btn => {
        if (btn.dataset.tone === state.selectedTone) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    // Reset Format Grid
    DOM.formatGrid.querySelectorAll('.option-card').forEach(btn => {
        if (btn.dataset.format === state.selectedFormat) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// 10. GENERATION PIPELINE & SERVICES
async function generateCopilotOutput() {
    if (!state.selectedArticle || state.isGenerating) return;
    
    state.isGenerating = true;
    DOM.generateBtn.disabled = true;
    
    // Reset result UI
    DOM.outputContainer.classList.remove('hidden');
    DOM.generationLoader.classList.remove('hidden');
    DOM.outputTextArea.value = '';
    
    // Copy/Download actions should be invisible during generation
    DOM.copyBtn.style.display = 'none';
    DOM.downloadBtn.style.display = 'none';
    
    const requestData = {
        title: state.selectedArticle.title,
        summary: state.selectedArticle.summary,
        authors: state.selectedArticle.authors,
        link: state.selectedArticle.link,
        category: state.selectedArticle.category,
        tone: state.selectedTone,
        format: state.selectedFormat
    };
    
    try {
        // Fetch generated content from back-end generator endpoint
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            DOM.generationLoader.classList.add('hidden');
            
            // Show action buttons
            DOM.copyBtn.style.display = 'inline-flex';
            DOM.downloadBtn.style.display = 'inline-flex';
            
            // Trigger typing effect for premium look and feel
            typeTextEffect(DOM.outputTextArea, data.output);
        } else {
            DOM.generationLoader.classList.add('hidden');
            DOM.outputTextArea.value = `Error generating content: ${data.error}`;
        }
    } catch (error) {
        console.error('Generation call failed:', error);
        DOM.generationLoader.classList.add('hidden');
        DOM.outputTextArea.value = 'Failed to generate output due to a network connection error.';
    } finally {
        state.isGenerating = false;
        DOM.generateBtn.disabled = false;
    }
}

// Premium visual micro-animation typing effect
function typeTextEffect(element, text) {
    let index = 0;
    element.value = '';
    
    // Split into characters or small chunks to speed up slightly
    // Typing single character is standard, but for longer summaries, chunk-typing is faster and avoids lag
    const chunkSize = Math.max(1, Math.floor(text.length / 80)); // Complete typing in about 1-2 seconds
    
    function type() {
        if (index < text.length) {
            element.value += text.substring(index, index + chunkSize);
            index += chunkSize;
            element.scrollTop = element.scrollHeight; // Auto scroll down
            setTimeout(type, 15);
        } else {
            element.value = text; // Hard complete to catch rounding errors
        }
    }
    
    type();
}

// 11. CLIPBOARD COPY ENGINE
async function copyToClipboard() {
    const text = DOM.outputTextArea.value;
    if (!text) return;
    
    try {
        await navigator.clipboard.writeText(text);
        
        // Show success animation state
        DOM.copyBtn.classList.add('copied');
        DOM.copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> <span>Copied!</span>';
        
        setTimeout(() => {
            DOM.copyBtn.classList.remove('copied');
            DOM.copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i> <span>Copy</span>';
        }, 2000);
    } catch (err) {
        console.error('Failed to copy text:', err);
    }
}

// 12. TEXT FILE COMPILER & DOWNLOADER
function downloadOutputAsText() {
    const text = DOM.outputTextArea.value;
    if (!text || !state.selectedArticle) return;
    
    const slug = state.selectedArticle.title
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')
        .substring(0, 30);
        
    const filename = `${slug}_${state.selectedFormat}.txt`;
    
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const link = document.createElement('a');
    
    if (window.navigator.msSaveOrOpenBlob) {
        window.navigator.msSaveOrOpenBlob(blob, filename);
    } else {
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
    }
}

// 13. UI METADATA HELPERS
function populateFilterOptions() {
    // Populate Source Dropdown
    const currentSource = DOM.sourceSelect.value;
    DOM.sourceSelect.innerHTML = '<option value="all">All Sources</option>';
    
    state.sources.forEach(source => {
        const option = document.createElement('option');
        option.value = source;
        option.textContent = source;
        DOM.sourceSelect.appendChild(option);
    });
    DOM.sourceSelect.value = currentSource;
}

function toggleClearSearchButton() {
    if (state.searchQuery) {
        DOM.clearSearchBtn.classList.add('visible');
    } else {
        DOM.clearSearchBtn.classList.remove('visible');
    }
}

function formatTimestamp(rawTimestamp) {
    // rawTimestamp is YYYY-MM-DD HH:MM:SS
    try {
        const parts = rawTimestamp.split(' ');
        const dateParts = parts[0].split('-');
        const timeParts = parts[1].split(':');
        
        const date = new Date(
            parseInt(dateParts[0]),
            parseInt(dateParts[1]) - 1,
            parseInt(dateParts[2]),
            parseInt(timeParts[0]),
            parseInt(timeParts[1]),
            parseInt(timeParts[2])
        );
        
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' (' + date.toLocaleDateString() + ')';
    } catch (e) {
        return rawTimestamp;
    }
}

function formatTimestampFriendly(rawDateStr) {
    // published formatted YYYY-MM-DD HH:MM:SS
    try {
        const d = new Date(rawDateStr);
        return d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
    } catch (e) {
        return rawDateStr;
    }
}

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
