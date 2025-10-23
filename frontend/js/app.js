// OpenGovt - Main Application Logic

// Constants
const MOCK_USER_NAME = 'Current User';

class OpenGovtApp {
  constructor() {
    this.currentPolitician = null;
    this.currentView = 'home';
    this.init();
  }

  init() {
    // Initialize app
    this.setupEventListeners();
    this.loadHomePage();
  }

  setupEventListeners() {
    // Logo click - return to home
    const logo = document.querySelector('.logo');
    if (logo) {
      logo.addEventListener('click', (e) => {
        e.preventDefault();
        this.loadHomePage();
      });
    }

    // Search functionality
    const searchInput = document.querySelector('.search-bar input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.handleSearch(e.target.value);
      });
    }
  }

  handleSearch(query) {
    if (query.trim().length < 2) return;
    
    const results = mockData.politicians.filter(p => 
      p.name.toLowerCase().includes(query.toLowerCase()) ||
      p.state.toLowerCase().includes(query.toLowerCase()) ||
      p.party.toLowerCase().includes(query.toLowerCase())
    );
    
    // Could display search results in a dropdown
    console.log('Search results:', results);
  }

  loadHomePage() {
    this.currentView = 'home';
    this.currentPolitician = mockData.politicians[0]; // Default to first politician
    this.renderSidebar();
    this.renderProfile(this.currentPolitician);
    this.renderFeed(this.currentPolitician.id);
    this.renderRightSidebar();
  }

  loadPoliticianProfile(politicianId) {
    this.currentPolitician = mockData.politicians.find(p => p.id === politicianId);
    if (!this.currentPolitician) return;
    
    this.currentView = 'profile';
    this.renderProfile(this.currentPolitician);
    this.renderFeed(politicianId);
  }

  renderSidebar() {
    const sidebar = document.querySelector('.sidebar');
    if (!sidebar) return;

    const html = `
      <div class="sidebar-section">
        <h3>Politicians</h3>
        ${mockData.politicians.map(politician => `
          <a href="#" class="politician-list-item" data-politician-id="${politician.id}">
            <img src="${politician.image}" alt="${politician.name}">
            <div class="politician-list-item-info">
              <div class="politician-list-item-name">${politician.name}</div>
              <div class="politician-list-item-role">${politician.role}</div>
            </div>
          </a>
        `).join('')}
      </div>
      
      <div class="sidebar-section">
        <h3>States</h3>
        ${mockData.states.map(state => `
          <a href="#" class="politician-list-item">
            <img src="${state.image}" alt="${state.name}">
            <div class="politician-list-item-info">
              <div class="politician-list-item-name">${state.name}</div>
              <div class="politician-list-item-role">${state.governor}</div>
            </div>
          </a>
        `).join('')}
      </div>
    `;

    sidebar.innerHTML = html;

    // Add click handlers to politician links
    sidebar.querySelectorAll('.politician-list-item[data-politician-id]').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const politicianId = parseInt(link.dataset.politicianId);
        this.loadPoliticianProfile(politicianId);
      });
    });
  }

  renderProfile(politician) {
    const mainFeed = document.querySelector('.main-feed');
    if (!mainFeed) return;

    const partyClass = politician.party.toLowerCase();

    const profileHtml = `
      <div class="profile-header">
        <div class="profile-cover"></div>
        <div class="profile-info">
          <div class="profile-picture-wrapper">
            <img src="${politician.image}" alt="${politician.name}" class="profile-picture">
          </div>
          <h1 class="profile-name">${politician.name}</h1>
          <div class="profile-role">${politician.role} • ${politician.state} ${politician.district !== 'At-Large' ? '• ' + politician.district : ''}</div>
          <span class="profile-party ${partyClass}">${politician.party}</span>
          <p class="profile-bio">${politician.bio}</p>
          <div class="profile-stats">
            <div class="stat">
              <div class="stat-value">${politician.stats.votesParticipated}</div>
              <div class="stat-label">Votes Participated</div>
            </div>
            <div class="stat">
              <div class="stat-value">${politician.stats.billsSponsored}</div>
              <div class="stat-label">Bills Sponsored</div>
            </div>
            <div class="stat">
              <div class="stat-value">${politician.stats.voteAlignment}%</div>
              <div class="stat-label">Party Alignment</div>
            </div>
            <div class="stat">
              <div class="stat-value">${politician.stats.approval}%</div>
              <div class="stat-label">Approval Rating</div>
            </div>
          </div>
        </div>
      </div>
    `;

    // Clear main feed and add profile
    mainFeed.innerHTML = profileHtml;
  }

  renderFeed(politicianId) {
    const mainFeed = document.querySelector('.main-feed');
    if (!mainFeed) return;

    // Get feed items for this politician
    const feedItems = mockData.feedItems
      .filter(item => item.politicianId === politicianId)
      .sort((a, b) => b.timestamp - a.timestamp);

    const feedHtml = feedItems.map(item => this.renderFeedItem(item)).join('');
    
    // Append to main feed (after profile header)
    mainFeed.innerHTML += feedHtml;

    // Add event listeners for actions
    this.setupFeedItemListeners();
  }

  renderFeedItem(item) {
    const politician = mockData.politicians.find(p => p.id === item.politicianId);
    const timeAgo = this.getTimeAgo(item.timestamp);
    
    let contentHtml = '';
    
    switch (item.type) {
      case 'vote':
        contentHtml = this.renderVoteContent(item);
        break;
      case 'social':
        contentHtml = this.renderSocialContent(item);
        break;
      case 'analytics':
        contentHtml = this.renderAnalyticsContent(item);
        break;
      case 'research':
        contentHtml = this.renderResearchContent(item);
        break;
    }

    const comments = mockData.comments[item.id] || [];
    const commentsHtml = this.renderComments(item.id, comments);

    return `
      <div class="feed-item" data-item-id="${item.id}">
        <div class="feed-item-header">
          <img src="${politician.image}" alt="${politician.name}" class="feed-item-avatar">
          <div class="feed-item-meta">
            <div>
              <span class="feed-item-author">${politician.name}</span>
              <span class="feed-item-type-badge ${item.type}">${item.type}</span>
            </div>
            <div class="feed-item-timestamp">${timeAgo}</div>
          </div>
        </div>
        
        ${contentHtml}
        
        <div class="feed-actions">
          <button class="action-btn like-btn" data-item-id="${item.id}">
            <span>👍</span>
            <span>${item.likes} Likes</span>
          </button>
          <button class="action-btn comment-btn" data-item-id="${item.id}">
            <span>💬</span>
            <span>${comments.length} Comments</span>
          </button>
          <button class="action-btn share-btn" data-item-id="${item.id}">
            <span>↗️</span>
            <span>Share</span>
          </button>
        </div>
        
        ${commentsHtml}
      </div>
    `;
  }

  renderVoteContent(item) {
    const vote = item.vote;
    return `
      <div class="vote-content">
        <div class="vote-bill">
          <span class="vote-bill-number">${vote.billNumber}</span> - ${vote.billTitle}
        </div>
        <div class="vote-description">${vote.description}</div>
        <div class="vote-result-container">
          <div class="vote-cast ${vote.vote.toLowerCase()}">${vote.vote}</div>
          <div class="vote-tallies">
            <div class="vote-tally">
              <span class="vote-tally-label">Yeas</span>
              <span class="vote-tally-value">${vote.yeas}</span>
            </div>
            <div class="vote-tally">
              <span class="vote-tally-label">Nays</span>
              <span class="vote-tally-value">${vote.nays}</span>
            </div>
          </div>
          <div class="vote-result ${vote.result.toLowerCase()}">${vote.result}</div>
        </div>
      </div>
    `;
  }

  renderSocialContent(item) {
    const social = item.social;
    const platformIcon = social.platform === 'twitter' ? '🐦' : '📘';
    return `
      <div class="social-content">
        <div class="social-platform">${platformIcon} ${social.platform}</div>
        <div class="social-text">${social.content}</div>
      </div>
    `;
  }

  renderAnalyticsContent(item) {
    const analytics = item.analytics;
    return `
      <div class="analytics-content">
        <h3 class="analytics-title">${analytics.title}</h3>
        <div class="kpis-grid">
          ${analytics.kpis.map(kpi => `
            <div class="kpi-card">
              <div class="kpi-value">
                ${kpi.value}
                <span class="kpi-trend ${kpi.trend}">
                  ${kpi.trend === 'up' ? '↗' : kpi.trend === 'down' ? '↘' : '→'}
                </span>
              </div>
              <div class="kpi-label">${kpi.label}</div>
            </div>
          `).join('')}
        </div>
        <div class="analytics-summary">${analytics.summary}</div>
      </div>
    `;
  }

  renderResearchContent(item) {
    const research = item.research;
    return `
      <div class="research-content">
        <h3 class="research-title">${research.title}</h3>
        <div class="research-author">📊 ${research.author}</div>
        <div class="research-findings">
          <ul>
            ${research.findings.map(finding => `<li>${finding}</li>`).join('')}
          </ul>
        </div>
        <div class="research-methodology">
          <strong>Methodology:</strong> ${research.methodology}
        </div>
      </div>
    `;
  }

  renderComments(itemId, comments) {
    const commentsHtml = comments.map(comment => {
      const timeAgo = this.getTimeAgo(comment.timestamp);
      const initials = comment.author.split(' ').filter(n => n).map(n => n[0]).join('');
      
      return `
        <div class="comment">
          <div class="comment-avatar">${initials}</div>
          <div class="comment-content">
            <div class="comment-bubble">
              <div class="comment-author">${comment.author}</div>
              <div class="comment-text">${comment.content}</div>
            </div>
            <div class="comment-meta">
              <span>${timeAgo}</span>
              <span class="comment-like" data-comment-id="${comment.id}">👍 ${comment.likes}</span>
              <span>Reply</span>
            </div>
          </div>
        </div>
      `;
    }).join('');

    return `
      <div class="comments-section ${comments.length === 0 ? 'hidden' : ''}" data-item-id="${itemId}">
        ${commentsHtml}
        <div class="comment-form">
          <div class="comment-form-avatar">U</div>
          <div class="comment-input-wrapper">
            <textarea 
              class="comment-input" 
              placeholder="Write a comment..." 
              rows="1"
              data-item-id="${itemId}"
            ></textarea>
            <button class="comment-submit" data-item-id="${itemId}" disabled>Post</button>
          </div>
        </div>
      </div>
    `;
  }

  setupFeedItemListeners() {
    // Like buttons
    document.querySelectorAll('.like-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.handleLike(parseInt(btn.dataset.itemId));
      });
    });

    // Comment buttons - toggle comments section
    document.querySelectorAll('.comment-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const itemId = parseInt(btn.dataset.itemId);
        const commentsSection = document.querySelector(`.comments-section[data-item-id="${itemId}"]`);
        if (commentsSection) {
          commentsSection.classList.toggle('hidden');
          if (!commentsSection.classList.contains('hidden')) {
            const input = commentsSection.querySelector('.comment-input');
            if (input) input.focus();
          }
        }
      });
    });

    // Comment inputs
    document.querySelectorAll('.comment-input').forEach(input => {
      input.addEventListener('input', (e) => {
        const submitBtn = input.parentElement.querySelector('.comment-submit');
        submitBtn.disabled = e.target.value.trim().length === 0;
      });
      
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          const itemId = parseInt(input.dataset.itemId);
          this.handleComment(itemId, input.value);
        }
      });
    });

    // Comment submit buttons
    document.querySelectorAll('.comment-submit').forEach(btn => {
      btn.addEventListener('click', () => {
        const itemId = parseInt(btn.dataset.itemId);
        const input = document.querySelector(`.comment-input[data-item-id="${CSS.escape(itemId.toString())}"]`);
        if (input && input.value.trim()) {
          this.handleComment(itemId, input.value);
        }
      });
    });
  }

  handleLike(itemId) {
    const item = mockData.feedItems.find(i => i.id === itemId);
    if (item) {
      item.likes += 1;
      
      // Update the UI
      const likeBtn = document.querySelector(`.like-btn[data-item-id="${itemId}"]`);
      if (likeBtn) {
        const likeText = likeBtn.querySelector('span:last-child');
        if (likeText) {
          likeText.textContent = `${item.likes} Likes`;
        }
        likeBtn.classList.add('active');
      }
    }
  }

  handleComment(itemId, content) {
    if (!content.trim()) return;
    
    // Create new comment
    const newComment = {
      id: Date.now(),
      author: MOCK_USER_NAME, // In a real app, this would be the logged-in user
      content: content.trim(),
      timestamp: new Date(),
      likes: 0
    };
    
    // Add to comments
    if (!mockData.comments[itemId]) {
      mockData.comments[itemId] = [];
    }
    mockData.comments[itemId].push(newComment);
    
    // Update the feed item
    const feedItem = mockData.feedItems.find(i => i.id === itemId);
    if (feedItem) {
      feedItem.comments = mockData.comments[itemId];
    }
    
    // Re-render just this feed item
    const feedItemElement = document.querySelector(`.feed-item[data-item-id="${itemId}"]`);
    if (feedItemElement) {
      const newItemHtml = this.renderFeedItem(feedItem);
      const temp = document.createElement('div');
      temp.innerHTML = newItemHtml;
      feedItemElement.replaceWith(temp.firstElementChild);
      
      // Re-setup listeners
      this.setupFeedItemListeners();
      
      // Show comments section
      const commentsSection = document.querySelector(`.comments-section[data-item-id="${itemId}"]`);
      if (commentsSection) {
        commentsSection.classList.remove('hidden');
      }
    }
  }

  getTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    
    let interval = Math.floor(seconds / 31536000);
    if (interval >= 1) return interval + ' year' + (interval === 1 ? '' : 's') + ' ago';
    
    interval = Math.floor(seconds / 2592000);
    if (interval >= 1) return interval + ' month' + (interval === 1 ? '' : 's') + ' ago';
    
    interval = Math.floor(seconds / 86400);
    if (interval >= 1) return interval + ' day' + (interval === 1 ? '' : 's') + ' ago';
    
    interval = Math.floor(seconds / 3600);
    if (interval >= 1) return interval + ' hour' + (interval === 1 ? '' : 's') + ' ago';
    
    interval = Math.floor(seconds / 60);
    if (interval >= 1) return interval + ' minute' + (interval === 1 ? '' : 's') + ' ago';
    
    return Math.floor(seconds) + ' seconds ago';
  }

  renderRightSidebar() {
    const rightSidebar = document.querySelector('.right-sidebar');
    if (!rightSidebar) return;

    const html = `
      <div class="trending-section">
        <h3>Trending Topics</h3>
        <div class="trending-item">
          <div class="trending-category">Politics • Trending</div>
          <div class="trending-title">Climate Action Act</div>
          <div class="trending-count">1.2K discussions</div>
        </div>
        <div class="trending-item">
          <div class="trending-category">Economy • Trending</div>
          <div class="trending-title">Tax Relief Proposals</div>
          <div class="trending-count">892 discussions</div>
        </div>
        <div class="trending-item">
          <div class="trending-category">Healthcare • Trending</div>
          <div class="trending-title">Medicare Expansion</div>
          <div class="trending-count">645 discussions</div>
        </div>
        <div class="trending-item">
          <div class="trending-category">Education • Trending</div>
          <div class="trending-title">School Funding Reform</div>
          <div class="trending-count">523 discussions</div>
        </div>
      </div>
      
      <div class="trending-section">
        <h3>Recent Bills</h3>
        <div class="trending-item">
          <div class="trending-category">H.R. 1234</div>
          <div class="trending-title">Climate Action and Clean Energy Act</div>
          <div class="trending-count">Passed • 235-200</div>
        </div>
        <div class="trending-item">
          <div class="trending-category">S. 567</div>
          <div class="trending-title">Tax Relief and Economic Growth Act</div>
          <div class="trending-count">Passed • 221-214</div>
        </div>
        <div class="trending-item">
          <div class="trending-category">H.R. 2891</div>
          <div class="trending-title">Border Security Enhancement Act</div>
          <div class="trending-count">Passed • 228-207</div>
        </div>
      </div>
    `;

    rightSidebar.innerHTML = html;
  }
}

// Initialize the app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.app = new OpenGovtApp();
});
