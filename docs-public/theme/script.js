// SAGE Landing Page JavaScript

// Floating navigation scroll effect
window.addEventListener('scroll', function() {
    const floatingNav = document.getElementById('floatingNav');
    if (window.scrollY > window.innerHeight * 0.3) {
        floatingNav.classList.add('visible');
    } else {
        floatingNav.classList.remove('visible');
    }
});

// Intersection Observer for animations
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver(function(entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
            entry.target.classList.add('visible');

            // 先检测屏幕宽度，只在768px以下时强制设置step-card的高度
            const el = entry.target;
            if (window.innerWidth <= 768) {
                if (el.classList.contains('step-card') && el.classList.contains('compact')) {
                    const stepExplanation = el.closest('.step-explanation');
                    if (stepExplanation) {
                        const stepId = stepExplanation.id;
                        if (stepId === 'step-1' || stepId === 'step-3') {
                            el.style.height = '300px';
                            el.style.minHeight = '300px';
                            el.style.maxHeight = '300px';
                        } else if (stepId === 'step-2' || stepId === 'step-4') {
                            el.style.height = '300px';
                            el.style.minHeight = '300px';
                            el.style.maxHeight = '300px';
                        }
                    }
                }
            }
        }
    });
}, observerOptions);

// Observe feature cards and other elements
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.feature-card, .step-card, .section-animate').forEach(el => {
        // Set initial animation state
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'all 0.6s ease';
        observer.observe(el);

        // Check if element is already in viewport
        const rect = el.getBoundingClientRect();
        const isInViewport = rect.top < window.innerHeight && rect.bottom > 0;
        if (isInViewport) {
            setTimeout(() => {
                el.style.opacity = '1';
                el.style.transform = 'translateY(0)';
                el.classList.add('visible');

                // 先检测屏幕宽度，只在768px以下时强制设置step-card的高度
                if (window.innerWidth <= 768) {
                    if (el.classList.contains('step-card') && el.classList.contains('compact')) {
                        const stepExplanation = el.closest('.step-explanation');
                        if (stepExplanation) {
                            const stepId = stepExplanation.id;
                            if (stepId === 'step-1' || stepId === 'step-3') {
                                el.style.height = '200px';
                                el.style.minHeight = '200px';
                                el.style.maxHeight = '200px';
                            } else if (stepId === 'step-2' || stepId === 'step-4') {
                                el.style.height = '220px';
                                el.style.minHeight = '220px';
                                el.style.maxHeight = '220px';
                            }
                        }
                    }
                }
            }, 100);
        }
    });
});

// Add some interactive effects
document.querySelectorAll('.btn').forEach(btn => {
    btn.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-3px) scale(1.02)';
    });

    btn.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0) scale(1)';
    });
});

// Enhanced dynamic background effects
function createStreamingData() {
    const hero = document.querySelector('.hero');
    const dataNodesContainer = document.querySelector('.data-nodes');

    // Create additional flowing data particles
    for (let i = 0; i < 20; i++) {
        setTimeout(() => {
            const particle = document.createElement('div');
            particle.className = 'data-node';
            particle.style.cssText = `
                top: ${Math.random() * 100}%;
                left: -10px;
                background: ${['rgba(59, 130, 246, 0.8)', 'rgba(147, 51, 234, 0.8)', 'rgba(16, 185, 129, 0.8)', 'rgba(245, 158, 11, 0.8)'][Math.floor(Math.random() * 4)]};
                animation-duration: ${8 + Math.random() * 4}s;
                animation-delay: ${Math.random() * 2}s;
            `;
            dataNodesContainer.appendChild(particle);

            // Remove particle after animation
            setTimeout(() => {
                if (particle.parentNode) {
                    particle.parentNode.removeChild(particle);
                }
            }, 12000);
        }, i * 300);
    }
}

// Create starfield
function createStarfield() {
    const starfield = document.querySelector('.starfield');

    // Create 150 stars
    for (let i = 0; i < 150; i++) {
        const star = document.createElement('div');
        star.className = 'star';
        star.style.cssText = `
            top: ${Math.random() * 100}%;
            left: ${Math.random() * 100}%;
            animation-delay: ${Math.random() * 3}s;
        `;
        starfield.appendChild(star);
    }
}

// Create floating data labels with boxes
function createDataLabels() {
    const labels = [
        { text: 'RAG', class: '' },
        { text: 'Vector DB', class: 'purple' },
        { text: 'Streaming', class: 'green' },
        { text: 'AI Agent', class: 'orange' },
        { text: 'ML Pipeline', class: '' },
        { text: 'DataFlow', class: 'purple' },
        { text: 'MCP', class: 'green' },
        { text: 'Multi Agent', class: 'orange' },
        { text: 'Online Learning', class: '' },
        { text: 'Streaming Benchmark', class: 'purple' },
        { text: 'Embodied Intelligence', class: 'green' },
        { text: 'Neural Memory', class: 'orange' },
        { text: 'Real-time Analytics', class: '' },
        { text: 'Distributed Computing', class: 'purple' }
    ];
    const hero = document.querySelector('.hero');

    labels.forEach((label, index) => {
        setTimeout(() => {
            const labelEl = document.createElement('div');
            labelEl.textContent = label.text;
            labelEl.className = `data-label ${label.class}`;
            labelEl.style.cssText = `
                top: ${20 + Math.random() * 60}%;
                left: -200px;
                animation-delay: ${Math.random() * 3}s;
            `;
            hero.appendChild(labelEl);

            setTimeout(() => {
                if (labelEl.parentNode) {
                    labelEl.parentNode.removeChild(labelEl);
                }
            }, 15000);
        }, index * 2000);
    });
}

// Start all animations
createStarfield();
createStreamingData();
setInterval(createStreamingData, 10000);

createDataLabels();
setInterval(createDataLabels, 25000);

// Mouse move parallax effect
document.addEventListener('mousemove', function(e) {
    const hero = document.querySelector('.hero');
    const nodes = document.querySelectorAll('.data-node');
    const stars = document.querySelectorAll('.star');
    const mouseX = e.clientX / window.innerWidth;
    const mouseY = e.clientY / window.innerHeight;

    nodes.forEach((node, index) => {
        const speed = (index % 3 + 1) * 0.5;
        const x = (mouseX - 0.5) * speed * 20;
        const y = (mouseY - 0.5) * speed * 20;
        node.style.transform += ` translate(${x}px, ${y}px)`;
    });

    // Add subtle parallax to stars
    stars.forEach((star, index) => {
        if (index % 10 === 0) { // Only affect every 10th star for performance
            const speed = 0.1;
            const x = (mouseX - 0.5) * speed * 10;
            const y = (mouseY - 0.5) * speed * 10;
            star.style.transform = `translate(${x}px, ${y}px)`;
        }
    });
});

// Parallax effect for hero section (reduced intensity)
window.addEventListener('scroll', function() {
    const scrolled = window.pageYOffset;
    const hero = document.querySelector('.hero');
    if (hero && scrolled < window.innerHeight) {
        hero.style.transform = `translateY(${scrolled * 0.3}px)`;
    }
});

// Tab switching functionality for Quick Start section
document.addEventListener('DOMContentLoaded', function() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');

            // Remove active class from all buttons and contents
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));

            // Add active class to clicked button and corresponding content
            this.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
        });
    });
});

// Video placeholder click handlers
document.addEventListener('DOMContentLoaded', function() {
    const videoPlaceholders = document.querySelectorAll('.video-placeholder');

    videoPlaceholders.forEach(placeholder => {
        placeholder.addEventListener('click', function() {
            // Add a simple click effect
            const playButton = this.querySelector('.play-button');
            playButton.style.transform = 'scale(0.9)';

            setTimeout(() => {
                playButton.style.transform = 'scale(1.1)';
            }, 150);

            setTimeout(() => {
                playButton.style.transform = 'scale(1)';
            }, 300);

            // You can add actual video loading logic here
            console.log('Video placeholder clicked - implement video loading');
        });
    });
});

// Enhanced hover effects for cards
document.addEventListener('DOMContentLoaded', function() {
    // Add hover effects to various card elements
    const cards = document.querySelectorAll('.feature-card, .why-card, .example-card, .contribute-card, .opportunity-card');

    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        });
    });

    // Add click effects to contribute links
    const contributeLinks = document.querySelectorAll('.contribute-link');
    contributeLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Add ripple effect
            const ripple = document.createElement('span');
            ripple.style.cssText = `
                position: absolute;
                border-radius: 50%;
                background: rgba(59, 130, 246, 0.3);
                transform: scale(0);
                animation: ripple 0.6s linear;
                pointer-events: none;
            `;

            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
            ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';

            this.style.position = 'relative';
            this.appendChild(ripple);

            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
});

// Smooth scrolling for anchor links
document.addEventListener('DOMContentLoaded', function() {
    const links = document.querySelectorAll('a[href^="#"]');

    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);

            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});

// Add CSS animation keyframes dynamically
const style = document.createElement('style');
style.textContent = `
    @keyframes ripple {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }

    @keyframes nodeFloat {
        0%, 100% { transform: translateX(0) translateY(0); }
        25% { transform: translateX(100vw) translateY(-20px); }
        50% { transform: translateX(100vw) translateY(20px); }
        75% { transform: translateX(100vw) translateY(-10px); }
    }

    @keyframes labelFlow {
        0% { transform: translateX(0); opacity: 0; }
        10% { opacity: 1; }
        90% { opacity: 1; }
        100% { transform: translateX(calc(100vw + 200px)); opacity: 0; }
    }

    @keyframes pulse {
        0%, 100% { opacity: 0.3; }
        50% { opacity: 0.8; }
    }

    @keyframes twinkle {
        0%, 100% { opacity: 0.3; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.2); }
    }

    @keyframes streamFlow {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }
`;
document.head.appendChild(style);

// Performance optimization: Throttle scroll events
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

// Apply throttling to scroll events
const throttledScrollHandler = throttle(function() {
    const floatingNav = document.getElementById('floatingNav');
    if (window.scrollY > window.innerHeight * 0.3) {
        floatingNav.classList.add('visible');
    } else {
        floatingNav.classList.remove('visible');
    }

    // Parallax effect
    const scrolled = window.pageYOffset;
    const hero = document.querySelector('.hero');
    if (hero && scrolled < window.innerHeight) {
        hero.style.transform = `translateY(${scrolled * 0.3}px)`;
    }
}, 16); // ~60fps

// Replace the existing scroll event listener with throttled version
window.addEventListener('scroll', throttledScrollHandler);

// Add missing playVideo function
function playVideo(videoId) {
    console.log('Playing video:', videoId);
    // Add actual video implementation here
    // For now, just show an alert or console message
    const videoElement = document.querySelector(`[onclick="playVideo('${videoId}')"]`);
    if (videoElement) {
        const overlay = videoElement.querySelector('.video-overlay h4');
        if (overlay) {
            const originalText = overlay.textContent;
            overlay.textContent = '正在加载视频...';
            setTimeout(() => {
                overlay.textContent = originalText;
            }, 2000);
        }
    }
}

// Fix section animation visibility issues
document.addEventListener('DOMContentLoaded', function() {
    // Ensure all section-animate elements are visible initially
    const sectionElements = document.querySelectorAll('.section-animate');
    sectionElements.forEach(el => {
        // Set initial state for better visibility
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
    });
});

// Article Monitoring Animation Controller
class ArticleMonitoringAnimation {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.isPlaying = false;
        this.currentPhase = 0;
        this.phaseTimer = null;
        this.animationLoop = null;
        this.phaseDuration = 7500; // 7.5 seconds per phase
        this.totalDuration = 30000; // 30 seconds total

        this.phases = [
            { name: 'Document Flow', duration: 7500 },
            { name: 'Processing', duration: 7500 },
            { name: 'Filtering', duration: 7500 },
            { name: 'Delivery', duration: 7500 }
        ];

        this.init();
    }

    init() {
        if (!this.container) return;

        this.createControls();
        this.createElements();
        this.bindEvents();

        // Auto-start animation
        setTimeout(() => this.play(), 1000);
    }

    createControls() {
        const controlsHTML = `
            <div class="animation-controls">
                <button class="control-btn play-pause-btn" title="播放/暂停">
                    <i class="fas fa-play"></i>
                </button>
                <button class="control-btn restart-btn" title="重新开始">
                    <i class="fas fa-redo"></i>
                </button>
            </div>
        `;
        this.container.insertAdjacentHTML('afterbegin', controlsHTML);

        this.playPauseBtn = this.container.querySelector('.play-pause-btn');
        this.restartBtn = this.container.querySelector('.restart-btn');
    }

    createElements() {
        const elementsHTML = `
            <!-- ArXiv Source -->
            <div class="arxiv-source">
                <i class="fas fa-file-alt"></i>
            </div>

            <!-- Document Flow -->
            <div class="document-flow">
                <div class="document" style="top: 45%;"></div>
                <div class="document" style="top: 50%;"></div>
                <div class="document" style="top: 55%;"></div>
                <div class="document" style="top: 48%;"></div>
            </div>

            <!-- Processing Pipeline -->
            <div class="processing-pipeline">
                <div class="process-stage text-parsing" data-label="文本解析">
                    <i class="fas fa-file-text"></i>
                </div>
                <div class="process-stage keyword-filter" data-label="关键词筛选">
                    <i class="fas fa-filter"></i>
                </div>
                <div class="process-stage semantic-analysis" data-label="语义分析">
                    <i class="fas fa-brain"></i>
                </div>
            </div>

            <!-- Neural Network Visualization -->
            <div class="neural-network">
                <div class="neural-layer input">
                    <div class="neural-node"></div>
                    <div class="neural-node"></div>
                    <div class="neural-node"></div>
                </div>
                <div class="neural-layer hidden">
                    <div class="neural-node"></div>
                    <div class="neural-node"></div>
                    <div class="neural-node"></div>
                    <div class="neural-node"></div>
                </div>
                <div class="neural-layer output">
                    <div class="neural-node"></div>
                    <div class="neural-node"></div>
                </div>
                <!-- Neural connections -->
                <div class="neural-connection" style="top: 10px; left: 12px; width: 28px;"></div>
                <div class="neural-connection" style="top: 18px; left: 12px; width: 28px;"></div>
                <div class="neural-connection" style="top: 26px; left: 12px; width: 28px;"></div>
                <div class="neural-connection" style="top: 10px; left: 52px; width: 28px;"></div>
                <div class="neural-connection" style="top: 18px; left: 52px; width: 28px;"></div>
            </div>

            <!-- User Interface -->
            <div class="user-interface">
                <i class="fas fa-user"></i>
            </div>

            <!-- Particle Effects -->
            <div class="particle accepted" style="top: 45%;"></div>
            <div class="particle accepted" style="top: 50%;"></div>
            <div class="particle rejected" style="top: 55%;"></div>
        `;

        this.container.insertAdjacentHTML('beforeend', elementsHTML);

        // Store references to key elements
        this.documents = this.container.querySelectorAll('.document');
        this.processStages = this.container.querySelectorAll('.process-stage');
        this.particles = this.container.querySelectorAll('.particle');
        this.neuralNetwork = this.container.querySelector('.neural-network');
        this.userInterface = this.container.querySelector('.user-interface');
    }

    bindEvents() {
        this.playPauseBtn.addEventListener('click', () => this.togglePlayPause());
        this.restartBtn.addEventListener('click', () => this.restart());

        // Hover effects
        this.container.addEventListener('mouseenter', () => this.onHover());
        this.container.addEventListener('mouseleave', () => this.onHoverEnd());

        // Phase indicators (optional)
        this.processStages.forEach((stage, index) => {
            stage.addEventListener('click', () => this.jumpToPhase(index + 1));
        });
    }

    play() {
        if (this.isPlaying) return;

        this.isPlaying = true;
        this.container.classList.add('playing');
        this.playPauseBtn.innerHTML = '<i class="fas fa-pause"></i>';
        this.playPauseBtn.classList.add('active');

        this.startAnimationLoop();
    }

    pause() {
        if (!this.isPlaying) return;

        this.isPlaying = false;
        this.container.classList.remove('playing');
        this.playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
        this.playPauseBtn.classList.remove('active');

        this.stopAnimationLoop();
    }

    togglePlayPause() {
        if (this.isPlaying) {
            this.pause();
        } else {
            this.play();
        }
    }

    restart() {
        this.pause();
        this.currentPhase = 0;

        // Reset all elements
        this.container.classList.remove('playing');

        // Small delay before restarting
        setTimeout(() => {
            this.play();
        }, 100);
    }

    startAnimationLoop() {
        this.animationLoop = setInterval(() => {
            this.updatePhase();
        }, this.phaseDuration);

        // Initial phase
        this.updatePhase();
    }

    stopAnimationLoop() {
        if (this.animationLoop) {
            clearInterval(this.animationLoop);
            this.animationLoop = null;
        }
    }

    updatePhase() {
        const phase = this.phases[this.currentPhase];

        // Add phase-specific effects
        this.triggerPhaseEffects(this.currentPhase);

        // Move to next phase
        this.currentPhase = (this.currentPhase + 1) % this.phases.length;
    }

    triggerPhaseEffects(phaseIndex) {
        // Remove previous phase classes
        this.container.classList.remove('phase-0', 'phase-1', 'phase-2', 'phase-3');

        // Add current phase class
        this.container.classList.add(`phase-${phaseIndex}`);

        switch (phaseIndex) {
            case 0: // Document Flow
                this.triggerDocumentFlow();
                break;
            case 1: // Processing
                this.triggerProcessing();
                break;
            case 2: // Filtering
                this.triggerFiltering();
                break;
            case 3: // Delivery
                this.triggerDelivery();
                break;
        }
    }

    triggerDocumentFlow() {
        // Documents start flowing from ArXiv
        this.documents.forEach((doc, index) => {
            setTimeout(() => {
                doc.style.animationDelay = `${index * 1.5}s`;
            }, index * 200);
        });
    }

    triggerProcessing() {
        // Activate processing stages sequentially
        this.processStages.forEach((stage, index) => {
            setTimeout(() => {
                stage.classList.add('active');
                setTimeout(() => stage.classList.remove('active'), 2000);
            }, index * 1000);
        });

        // Show neural network
        if (this.neuralNetwork) {
            this.neuralNetwork.style.opacity = '1';
        }
    }

    triggerFiltering() {
        // Show filtering decisions
        this.particles.forEach((particle, index) => {
            setTimeout(() => {
                particle.style.opacity = '1';
                if (particle.classList.contains('rejected')) {
                    particle.style.transform = 'translateY(-30%) translateX(100px) scale(0.5)';
                }
            }, index * 500);
        });
    }

    triggerDelivery() {
        // Highlight user interface
        if (this.userInterface) {
            this.userInterface.classList.add('active');
            setTimeout(() => this.userInterface.classList.remove('active'), 3000);
        }

        // Reset particles
        setTimeout(() => {
            this.particles.forEach(particle => {
                particle.style.opacity = '0';
                particle.style.transform = '';
            });
        }, 3000);
    }

    jumpToPhase(phaseIndex) {
        if (phaseIndex < 0 || phaseIndex >= this.phases.length) return;

        this.currentPhase = phaseIndex;
        this.triggerPhaseEffects(phaseIndex);
    }

    onHover() {
        // Add hover effects
        this.container.classList.add('hovered');
    }

    onHoverEnd() {
        // Remove hover effects
        this.container.classList.remove('hovered');
    }

    destroy() {
        this.pause();
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Initialize Article Monitoring Animation when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Create animation container if it doesn't exist
    const existingContainer = document.getElementById('articleMonitoringAnimation');
    if (!existingContainer) {
        // We'll create this when the HTML structure is added
        console.log('Article monitoring animation container not found. Will be created when HTML structure is added.');
    } else {
        // Initialize the animation
        window.articleMonitoringAnimation = new ArticleMonitoringAnimation('articleMonitoringAnimation');
    }
});

// Function to initialize animation (can be called from HTML)
function initializeArticleMonitoring(containerId = 'articleMonitoringAnimation') {
    if (window.articleMonitoringAnimation) {
        window.articleMonitoringAnimation.destroy();
    }
    window.articleMonitoringAnimation = new ArticleMonitoringAnimation(containerId);
}

// Performance optimization for animations
function optimizeAnimationPerformance() {
    // Use requestAnimationFrame for smooth animations
    const animationContainers = document.querySelectorAll('.article-monitoring-container');

    animationContainers.forEach(container => {
        // Enable hardware acceleration
        container.style.willChange = 'transform, opacity';

        // Use transform3d for better performance
        const animatedElements = container.querySelectorAll('.document, .particle, .process-stage');
        animatedElements.forEach(el => {
            el.style.transform += ' translateZ(0)';
        });
    });
}

// Call performance optimization
document.addEventListener('DOMContentLoaded', optimizeAnimationPerformance);

// Distributed Smart Home Animation Controller
class SmartHomeAnimation {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.isPlaying = false;
        this.currentPhase = 0;
        this.phaseTimer = null;
        this.animationLoop = null;
        this.phaseDuration = 6250; // 6.25 seconds per phase
        this.totalDuration = 25000; // 25 seconds total

        this.phases = [
            { name: 'Network Initialization', duration: 6250 },
            { name: 'Environmental Monitoring', duration: 6250 },
            { name: 'Laundry Process', duration: 6250 },
            { name: 'Completion & Reset', duration: 6250 }
        ];

        this.deviceStates = {
            robot: 'idle',
            washer: 'idle',
            dryer: 'idle',
            tempSensor: 'idle',
            humiditySensor: 'idle',
            motionSensor: 'idle'
        };

        this.init();
    }

    init() {
        if (!this.container) return;

        this.createControls();
        this.createElements();
        this.bindEvents();

        // Auto-start animation
        setTimeout(() => this.play(), 1000);
    }

    createControls() {
        const controlsHTML = `
            <div class="animation-controls">
                <button class="control-btn play-pause-btn" title="Play/Pause">
                    <i class="fas fa-play"></i>
                </button>
                <button class="control-btn restart-btn" title="Restart">
                    <i class="fas fa-redo"></i>
                </button>
                <button class="control-btn info-btn" title="Animation Info">
                    <i class="fas fa-info"></i>
                </button>
            </div>
        `;
        this.container.insertAdjacentHTML('afterbegin', controlsHTML);

        this.playPauseBtn = this.container.querySelector('.play-pause-btn');
        this.restartBtn = this.container.querySelector('.restart-btn');
        this.infoBtn = this.container.querySelector('.info-btn');
    }

    createElements() {
        const elementsHTML = `
            <!-- Laundry Robot -->
            <div class="laundry-robot" data-device="robot">
                <i class="fas fa-robot"></i>
                <div class="device-status idle"></div>
                <div class="device-tooltip">Laundry Robot<br>Status: <span class="status-text">Idle</span></div>
            </div>

            <!-- Washing Machine -->
            <div class="washing-machine" data-device="washer">
                <i class="fas fa-tint"></i>
                <div class="device-status idle"></div>
                <div class="device-tooltip">Washing Machine<br>Status: <span class="status-text">Idle</span></div>
            </div>

            <!-- Drying Rack -->
            <div class="drying-rack" data-device="dryer">
                <i class="fas fa-wind"></i>
                <div class="device-status idle"></div>
                <div class="device-tooltip">Drying Rack<br>Status: <span class="status-text">Idle</span></div>
            </div>

            <!-- Environmental Sensors -->
            <div class="environmental-sensor temp-sensor" data-device="tempSensor" data-label="Temp">
                <i class="fas fa-thermometer-half"></i>
                <div class="device-status idle"></div>
                <div class="device-tooltip">Temperature Sensor<br>Status: <span class="status-text">Idle</span></div>
            </div>

            <div class="environmental-sensor humidity-sensor" data-device="humiditySensor" data-label="Humid">
                <i class="fas fa-tint"></i>
                <div class="device-status idle"></div>
                <div class="device-tooltip">Humidity Sensor<br>Status: <span class="status-text">Idle</span></div>
            </div>

            <div class="environmental-sensor motion-sensor" data-device="motionSensor" data-label="Motion">
                <i class="fas fa-walking"></i>
                <div class="device-status idle"></div>
                <div class="device-tooltip">Motion Sensor<br>Status: <span class="status-text">Idle</span></div>
            </div>

            <!-- Network Connections -->
            <div class="network-connection robot-to-washer"></div>
            <div class="network-connection washer-to-dryer"></div>
            <div class="network-connection robot-to-sensors"></div>
            <div class="network-connection sensors-to-dryer"></div>

            <!-- Data Packets -->
            <div class="data-packet sensor-data" style="top: 20%; left: 30%;"></div>
            <div class="data-packet control-signal" style="top: 50%; left: 90px;"></div>
            <div class="data-packet status-update" style="top: 30%; left: 260px;"></div>
            <div class="data-packet error-signal" style="top: 70%; right: 30%;"></div>

            <!-- Laundry Items -->
            <div class="laundry-item" style="top: 32%; left: 210px;"></div>
            <div class="laundry-item" style="top: 28%; left: 215px;"></div>
            <div class="laundry-item" style="top: 32%; right: 210px;"></div>
            <div class="laundry-item" style="top: 28%; right: 215px;"></div>

            <!-- Phase Indicator -->
            <div class="phase-indicator">
                <div class="phase-text">Initializing...</div>
                <div class="phase-progress">
                    <div class="progress-bar"></div>
                </div>
            </div>
        `;

        this.container.insertAdjacentHTML('beforeend', elementsHTML);

        // Store references to key elements
        this.devices = {
            robot: this.container.querySelector('.laundry-robot'),
            washer: this.container.querySelector('.washing-machine'),
            dryer: this.container.querySelector('.drying-rack'),
            tempSensor: this.container.querySelector('.temp-sensor'),
            humiditySensor: this.container.querySelector('.humidity-sensor'),
            motionSensor: this.container.querySelector('.motion-sensor')
        };

        this.connections = this.container.querySelectorAll('.network-connection');
        this.dataPackets = this.container.querySelectorAll('.data-packet');
        this.laundryItems = this.container.querySelectorAll('.laundry-item');
        this.phaseIndicator = this.container.querySelector('.phase-indicator');
        this.phaseText = this.container.querySelector('.phase-text');
        this.progressBar = this.container.querySelector('.progress-bar');
    }

    bindEvents() {
        this.playPauseBtn.addEventListener('click', () => this.togglePlayPause());
        this.restartBtn.addEventListener('click', () => this.restart());
        this.infoBtn.addEventListener('click', () => this.showInfo());

        // Device click handlers for detailed status
        Object.values(this.devices).forEach(device => {
            device.addEventListener('click', (e) => this.onDeviceClick(e));
        });

        // Hover effects
        this.container.addEventListener('mouseenter', () => this.onHover());
        this.container.addEventListener('mouseleave', () => this.onHoverEnd());
    }

    play() {
        if (this.isPlaying) return;

        this.isPlaying = true;
        this.container.classList.add('playing');
        this.playPauseBtn.innerHTML = '<i class="fas fa-pause"></i>';
        this.playPauseBtn.classList.add('active');

        this.startAnimationLoop();
        this.updateProgressBar();
    }

    pause() {
        if (!this.isPlaying) return;

        this.isPlaying = false;
        this.container.classList.remove('playing');
        this.playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
        this.playPauseBtn.classList.remove('active');

        this.stopAnimationLoop();
    }

    togglePlayPause() {
        if (this.isPlaying) {
            this.pause();
        } else {
            this.play();
        }
    }

    restart() {
        this.pause();
        this.currentPhase = 0;
        this.resetDeviceStates();

        // Reset all elements
        this.container.classList.remove('playing');
        this.progressBar.style.width = '0%';

        // Small delay before restarting
        setTimeout(() => {
            this.play();
        }, 100);
    }

    startAnimationLoop() {
        this.animationLoop = setInterval(() => {
            this.updatePhase();
        }, this.phaseDuration);

        // Initial phase
        this.updatePhase();
    }

    stopAnimationLoop() {
        if (this.animationLoop) {
            clearInterval(this.animationLoop);
            this.animationLoop = null;
        }
    }

    updatePhase() {
        const phase = this.phases[this.currentPhase];
        this.phaseText.textContent = phase.name;

        // Add phase-specific effects
        this.triggerPhaseEffects(this.currentPhase);

        // Move to next phase
        this.currentPhase = (this.currentPhase + 1) % this.phases.length;
    }

    triggerPhaseEffects(phaseIndex) {
        // Remove previous phase classes
        this.container.classList.remove('phase-0', 'phase-1', 'phase-2', 'phase-3');

        // Add current phase class
        this.container.classList.add(`phase-${phaseIndex}`);

        switch (phaseIndex) {
            case 0: // Network Initialization
                this.triggerNetworkInit();
                break;
            case 1: // Environmental Monitoring
                this.triggerEnvironmentalMonitoring();
                break;
            case 2: // Laundry Process
                this.triggerLaundryProcess();
                break;
            case 3: // Completion & Reset
                this.triggerCompletion();
                break;
        }
    }

    triggerNetworkInit() {
        this.phaseText.textContent = 'Network Initialization';

        // Activate all devices sequentially
        setTimeout(() => this.updateDeviceState('robot', 'communicating'), 500);
        setTimeout(() => this.updateDeviceState('washer', 'communicating'), 1000);
        setTimeout(() => this.updateDeviceState('dryer', 'communicating'), 1500);
        setTimeout(() => this.updateDeviceState('tempSensor', 'communicating'), 2000);
        setTimeout(() => this.updateDeviceState('humiditySensor', 'communicating'), 2500);
        setTimeout(() => this.updateDeviceState('motionSensor', 'communicating'), 3000);

        // Show network connections
        this.connections.forEach((conn, index) => {
            setTimeout(() => {
                conn.style.opacity = '0.6';
            }, (index + 1) * 800);
        });
    }

    triggerEnvironmentalMonitoring() {
        this.phaseText.textContent = 'Environmental Monitoring';

        // Activate sensors
        this.updateDeviceState('tempSensor', 'active');
        this.updateDeviceState('humiditySensor', 'active');
        this.updateDeviceState('motionSensor', 'active');

        // Show data packets from sensors
        setTimeout(() => {
            this.dataPackets.forEach((packet, index) => {
                if (packet.classList.contains('sensor-data')) {
                    setTimeout(() => {
                        packet.style.opacity = '1';
                        this.animateDataPacket(packet, 'sensor');
                    }, index * 500);
                }
            });
        }, 1000);
    }

    triggerLaundryProcess() {
        this.phaseText.textContent = 'Laundry Process Execution';

        // Robot starts moving
        this.updateDeviceState('robot', 'active');

        // Washing machine activates
        setTimeout(() => {
            this.updateDeviceState('washer', 'active');
            this.laundryItems.forEach((item, index) => {
                setTimeout(() => {
                    item.style.opacity = '1';
                    item.classList.add('in-washer');
                }, index * 200);
            });
        }, 2000);

        // Transfer to dryer
        setTimeout(() => {
            this.updateDeviceState('dryer', 'active');
            this.laundryItems.forEach(item => {
                item.classList.remove('in-washer');
                item.classList.add('in-dryer');
            });
        }, 4000);
    }

    triggerCompletion() {
        this.phaseText.textContent = 'Process Complete';

        // All devices show completion status
        setTimeout(() => {
            Object.keys(this.devices).forEach(deviceKey => {
                this.updateDeviceState(deviceKey, 'idle');
            });

            // Hide laundry items
            this.laundryItems.forEach(item => {
                item.style.opacity = '0';
                item.classList.remove('in-washer', 'in-dryer');
            });

            // Fade network connections
            this.connections.forEach(conn => {
                conn.style.opacity = '0.2';
            });

            // Hide data packets
            this.dataPackets.forEach(packet => {
                packet.style.opacity = '0';
            });
        }, 2000);
    }

    updateDeviceState(deviceKey, state) {
        if (!this.devices[deviceKey]) return;

        this.deviceStates[deviceKey] = state;
        const device = this.devices[deviceKey];
        const statusIndicator = device.querySelector('.device-status');
        const statusText = device.querySelector('.status-text');

        // Update status indicator
        statusIndicator.className = `device-status ${state}`;

        // Update tooltip text
        if (statusText) {
            statusText.textContent = state.charAt(0).toUpperCase() + state.slice(1);
        }
    }

    animateDataPacket(packet, type) {
        // Set CSS custom properties for animation
        const startPos = this.getDevicePosition(type);
        const endPos = this.getTargetPosition(type);

        packet.style.setProperty('--start-x', startPos.x + 'px');
        packet.style.setProperty('--start-y', startPos.y + 'px');
        packet.style.setProperty('--end-x', endPos.x + 'px');
        packet.style.setProperty('--end-y', endPos.y + 'px');
    }

    getDevicePosition(type) {
        // Return approximate positions for data packet animations
        switch (type) {
            case 'sensor':
                return { x: 150, y: 100 };
            case 'robot':
                return { x: 70, y: 200 };
            case 'washer':
                return { x: 230, y: 120 };
            case 'dryer':
                return { x: 350, y: 120 };
            default:
                return { x: 200, y: 200 };
        }
    }

    getTargetPosition(type) {
        // Return target positions for data packets
        switch (type) {
            case 'sensor':
                return { x: 70, y: 200 }; // To robot
            case 'robot':
                return { x: 230, y: 120 }; // To washer
            case 'washer':
                return { x: 350, y: 120 }; // To dryer
            default:
                return { x: 200, y: 200 };
        }
    }

    updateProgressBar() {
        if (!this.isPlaying) return;

        const startTime = Date.now();
        const updateProgress = () => {
            if (!this.isPlaying) return;

            const elapsed = Date.now() - startTime;
            const progress = (elapsed % this.totalDuration) / this.totalDuration;
            this.progressBar.style.width = (progress * 100) + '%';

            requestAnimationFrame(updateProgress);
        };

        updateProgress();
    }

    onDeviceClick(event) {
        const device = event.currentTarget;
        const deviceType = device.getAttribute('data-device');
        const state = this.deviceStates[deviceType];

        // Show detailed device information
        this.showDeviceDetails(deviceType, state);

        // Add click effect
        device.style.transform += ' scale(0.95)';
        setTimeout(() => {
            device.style.transform = device.style.transform.replace(' scale(0.95)', '');
        }, 150);
    }

    showDeviceDetails(deviceType, state) {
        const deviceInfo = {
            robot: {
                name: 'Laundry Robot',
                description: 'Autonomous laundry handling robot',
                capabilities: ['Load/unload washing machine', 'Transfer items to dryer', 'Coordinate with other devices']
            },
            washer: {
                name: 'Smart Washing Machine',
                description: 'IoT-enabled washing machine',
                capabilities: ['Automatic cycle selection', 'Status reporting', 'Remote control']
            },
            dryer: {
                name: 'Smart Drying Rack',
                description: 'Intelligent drying system',
                capabilities: ['Humidity monitoring', 'Automatic drying', 'Completion notification']
            },
            tempSensor: {
                name: 'Temperature Sensor',
                description: 'Environmental temperature monitoring',
                capabilities: ['Real-time temperature data', 'Trend analysis', 'Alert system']
            },
            humiditySensor: {
                name: 'Humidity Sensor',
                description: 'Environmental humidity monitoring',
                capabilities: ['Humidity level tracking', 'Drying optimization', 'Mold prevention']
            },
            motionSensor: {
                name: 'Motion Sensor',
                description: 'Movement detection system',
                capabilities: ['Presence detection', 'Activity monitoring', 'Security integration']
            }
        };

        const info = deviceInfo[deviceType];
        if (info) {
            console.log(`${info.name} - Status: ${state}`);
            console.log(`Description: ${info.description}`);
            console.log('Capabilities:', info.capabilities);
        }
    }

    showInfo() {
        const infoText = `
Smart Home Laundry Automation System

Animation Phases:
1. Network Initialization (0-6.25s): Devices connect to network
2. Environmental Monitoring (6.25-12.5s): Sensors collect data
3. Laundry Process (12.5-18.75s): Robot coordinates washing/drying
4. Completion & Reset (18.75-25s): Process completes and resets

Click on devices for detailed information.
Hover over the animation for enhanced effects.
        `;

        alert(infoText);
    }

    resetDeviceStates() {
        Object.keys(this.deviceStates).forEach(key => {
            this.deviceStates[key] = 'idle';
            this.updateDeviceState(key, 'idle');
        });
    }

    onHover() {
        this.container.classList.add('hovered');
    }

    onHoverEnd() {
        this.container.classList.remove('hovered');
    }

    destroy() {
        this.pause();
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Initialize Smart Home Animation when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Create animation container if it doesn't exist
    const existingContainer = document.getElementById('smartHomeAnimation');
    if (!existingContainer) {
        console.log('Smart home animation container not found. Will be created when HTML structure is added.');
    } else {
        // Initialize the animation
        window.smartHomeAnimation = new SmartHomeAnimation('smartHomeAnimation');
    }
});

// Function to initialize smart home animation (can be called from HTML)
function initializeSmartHome(containerId = 'smartHomeAnimation') {
    if (window.smartHomeAnimation) {
        window.smartHomeAnimation.destroy();
    }
    window.smartHomeAnimation = new SmartHomeAnimation(containerId);
}

// Auto-Scaling Chat System Animation Controller
class AutoScalingAnimation {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.isPlaying = false;
        this.currentPhase = 0;
        this.phaseTimer = null;
        this.animationLoop = null;
        this.phaseDuration = 8750; // 8.75 seconds per phase
        this.totalDuration = 35000; // 35 seconds total

        this.phases = [
            { name: 'Initial Load', duration: 8750 },
            { name: 'Resource Optimization', duration: 8750 },
            { name: 'Scaling Triggered', duration: 8750 },
            { name: 'Load Distribution', duration: 8750 }
        ];

        this.userCount = 10;
        this.maxUsers = 1000;
        this.serverCount = 3;
        this.maxServers = 12;
        this.currentUtilization = { cpu: 30, memory: 40, network: 25 };

        this.init();
    }

    init() {
        if (!this.container) return;

        this.createControls();
        this.createElements();
        this.bindEvents();

        // Auto-start animation
        setTimeout(() => this.play(), 1000);
    }

    createControls() {
        const controlsHTML = `
            <div class="animation-controls">
                <button class="control-btn play-pause-btn" title="Play/Pause">
                    <i class="fas fa-play"></i>
                </button>
                <button class="control-btn restart-btn" title="Restart">
                    <i class="fas fa-redo"></i>
                </button>
                <button class="control-btn info-btn" title="Animation Info">
                    <i class="fas fa-info"></i>
                </button>
            </div>
        `;
        this.container.insertAdjacentHTML('afterbegin', controlsHTML);

        this.playPauseBtn = this.container.querySelector('.play-pause-btn');
        this.restartBtn = this.container.querySelector('.restart-btn');
        this.infoBtn = this.container.querySelector('.info-btn');
    }

    createElements() {
        const elementsHTML = `
            <!-- User Load Section -->
            <div class="user-load-section">
                <div class="user-load-title">Active Users</div>
                <div class="user-icons-grid">
                    ${Array.from({length: 64}, (_, i) => `<div class="user-icon" data-user="${i}"></div>`).join('')}
                </div>
                <div class="user-count-display">10</div>
            </div>

            <!-- Load Balancer -->
            <div class="load-balancer">
                <i class="fas fa-network-wired"></i>
                <div class="load-balancer-pulse"></div>
            </div>

            <!-- Server Grid -->
            <div class="server-grid">
                ${Array.from({length: 12}, (_, i) => `
                    <div class="server-instance ${i < 3 ? 'active' : ''}" data-server="${i}" data-tooltip="Server ${i + 1}">
                        <div class="server-label">S${i + 1}</div>
                        <div class="server-utilization">
                            <div class="utilization-bar" style="width: ${i < 3 ? Math.random() * 40 + 20 : 0}%;"></div>
                        </div>
                    </div>
                `).join('')}
            </div>

            <!-- Traffic Flow Lines -->
            <div class="traffic-flow user-to-lb"></div>
            <div class="traffic-flow lb-to-servers"></div>

            <!-- Scaling Trigger -->
            <div class="scaling-trigger">
                <i class="fas fa-exclamation-triangle"></i>
                <span class="trigger-text">High Load Detected</span>
            </div>

            <!-- Cloud Provider -->
            <div class="cloud-provider">
                <i class="fas fa-cloud"></i>
                <div class="cloud-spawn-effect"></div>
            </div>

            <!-- Resource Metrics Dashboard -->
            <div class="metrics-dashboard">
                <div class="metric-item">
                    <span class="metric-label">CPU</span>
                    <div class="metric-bar">
                        <div class="metric-fill cpu" style="width: 30%;"></div>
                    </div>
                    <span class="metric-value">30%</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">MEM</span>
                    <div class="metric-bar">
                        <div class="metric-fill memory" style="width: 40%;"></div>
                    </div>
                    <span class="metric-value">40%</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">NET</span>
                    <div class="metric-bar">
                        <div class="metric-fill network" style="width: 25%;"></div>
                    </div>
                    <span class="metric-value">25%</span>
                </div>
            </div>

            <!-- Interactive User Load Slider -->
            <div class="user-load-slider">
                <div class="slider-label">Adjust User Load</div>
                <input type="range" class="load-slider" min="10" max="1000" value="10" step="10">
                <div style="display: flex; justify-content: space-between; font-size: 8px; color: #94a3b8; margin-top: 4px;">
                    <span>10</span>
                    <span>1000</span>
                </div>
            </div>

            <!-- Phase Indicator -->
            <div class="phase-indicator" style="position: absolute; top: 15px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.7); color: white; padding: 6px 12px; border-radius: 6px; font-size: 11px; backdrop-filter: blur(10px);">
                <div class="phase-text">Initializing...</div>
                <div class="phase-progress" style="width: 100px; height: 2px; background: rgba(255,255,255,0.3); border-radius: 1px; margin-top: 4px; overflow: hidden;">
                    <div class="progress-bar" style="height: 100%; background: linear-gradient(90deg, #3b82f6, #10b981); width: 0%; transition: width 0.3s ease;"></div>
                </div>
            </div>
        `;

        this.container.insertAdjacentHTML('beforeend', elementsHTML);

        // Store references to key elements
        this.userIcons = this.container.querySelectorAll('.user-icon');
        this.userCountDisplay = this.container.querySelector('.user-count-display');
        this.serverInstances = this.container.querySelectorAll('.server-instance');
        this.utilizationBars = this.container.querySelectorAll('.utilization-bar');
        this.loadBalancer = this.container.querySelector('.load-balancer');
        this.scalingTrigger = this.container.querySelector('.scaling-trigger');
        this.metricsDashboard = this.container.querySelector('.metrics-dashboard');
        this.metricFills = this.container.querySelectorAll('.metric-fill');
        this.metricValues = this.container.querySelectorAll('.metric-value');
        this.trafficFlows = this.container.querySelectorAll('.traffic-flow');
        this.cloudSpawnEffect = this.container.querySelector('.cloud-spawn-effect');
        this.userLoadSlider = this.container.querySelector('.load-slider');
        this.phaseText = this.container.querySelector('.phase-text');
        this.progressBar = this.container.querySelector('.progress-bar');
    }

    bindEvents() {
        this.playPauseBtn.addEventListener('click', () => this.togglePlayPause());
        this.restartBtn.addEventListener('click', () => this.restart());
        this.infoBtn.addEventListener('click', () => this.showInfo());

        // User load slider interaction
        this.userLoadSlider.addEventListener('input', (e) => this.adjustUserLoad(parseInt(e.target.value)));

        // Server click handlers
        this.serverInstances.forEach((server, index) => {
            server.addEventListener('click', () => this.onServerClick(index));
        });

        // Load balancer click handler
        this.loadBalancer.addEventListener('click', () => this.onLoadBalancerClick());

        // Hover effects
        this.container.addEventListener('mouseenter', () => this.onHover());
        this.container.addEventListener('mouseleave', () => this.onHoverEnd());
    }

    play() {
        if (this.isPlaying) return;

        this.isPlaying = true;
        this.container.classList.add('playing');
        this.playPauseBtn.innerHTML = '<i class="fas fa-pause"></i>';
        this.playPauseBtn.classList.add('active');

        this.startAnimationLoop();
        this.updateProgressBar();
    }

    pause() {
        if (!this.isPlaying) return;

        this.isPlaying = false;
        this.container.classList.remove('playing');
        this.playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
        this.playPauseBtn.classList.remove('active');

        this.stopAnimationLoop();
    }

    togglePlayPause() {
        if (this.isPlaying) {
            this.pause();
        } else {
            this.play();
        }
    }

    restart() {
        this.pause();
        this.currentPhase = 0;
        this.userCount = 10;
        this.serverCount = 3;
        this.currentUtilization = { cpu: 30, memory: 40, network: 25 };

        // Reset all elements
        this.resetAnimation();

        // Small delay before restarting
        setTimeout(() => {
            this.play();
        }, 100);
    }

    startAnimationLoop() {
        this.animationLoop = setInterval(() => {
            this.updatePhase();
        }, this.phaseDuration);

        // Initial phase
        this.updatePhase();
    }

    stopAnimationLoop() {
        if (this.animationLoop) {
            clearInterval(this.animationLoop);
            this.animationLoop = null;
        }
    }

    updatePhase() {
        const phase = this.phases[this.currentPhase];
        this.phaseText.textContent = phase.name;

        // Add phase-specific effects
        this.triggerPhaseEffects(this.currentPhase);

        // Move to next phase
        this.currentPhase = (this.currentPhase + 1) % this.phases.length;
    }

    triggerPhaseEffects(phaseIndex) {
        // Remove previous phase classes
        this.container.classList.remove('phase-0', 'phase-1', 'phase-2', 'phase-3');

        // Add current phase class
        this.container.classList.add(`phase-${phaseIndex}`);

        switch (phaseIndex) {
            case 0: // Initial Load (0-8.75s)
                this.triggerInitialLoad();
                break;
            case 1: // Resource Optimization (8.75-17.5s)
                this.triggerResourceOptimization();
                break;
            case 2: // Scaling Triggered (17.5-26.25s)
                this.triggerScaling();
                break;
            case 3: // Load Distribution (26.25-35s)
                this.triggerLoadDistribution();
                break;
        }
    }

    triggerInitialLoad() {
        this.phaseText.textContent = 'Initial User Load';

        // Gradually increase user count
        this.animateUserGrowth(10, 100, 6000);

        // Show traffic flows
        setTimeout(() => {
            this.trafficFlows.forEach((flow, index) => {
                setTimeout(() => {
                    flow.style.opacity = '0.6';
                }, index * 500);
            });
        }, 1000);

        // Update metrics gradually
        this.animateMetrics({ cpu: 45, memory: 55, network: 40 }, 5000);
    }

    triggerResourceOptimization() {
        this.phaseText.textContent = 'Resource Optimization';

        // Continue user growth
        this.animateUserGrowth(100, 400, 7000);

        // Increase server utilization
        this.serverInstances.forEach((server, index) => {
            if (server.classList.contains('active')) {
                const utilizationBar = server.querySelector('.utilization-bar');
                setTimeout(() => {
                    utilizationBar.style.width = `${70 + Math.random() * 20}%`;
                }, index * 300);
            }
        });

        // Show load balancer stress
        setTimeout(() => {
            this.loadBalancer.style.animation = 'loadBalancerStress 2s infinite';
        }, 3000);

        // Update metrics to warning levels
        this.animateMetrics({ cpu: 75, memory: 80, network: 70 }, 4000);

        // Show scaling trigger warning
        setTimeout(() => {
            this.scalingTrigger.classList.add('active');
            this.scalingTrigger.querySelector('.trigger-text').textContent = 'Optimization Attempts';
        }, 5000);
    }

    triggerScaling() {
        this.phaseText.textContent = 'Auto-Scaling Triggered';

        // Critical user load
        this.animateUserGrowth(400, 800, 6000);

        // Show critical scaling trigger
        this.scalingTrigger.classList.add('critical');
        this.scalingTrigger.querySelector('.trigger-text').textContent = 'Scaling Threshold Reached!';

        // Trigger cloud spawn effect
        setTimeout(() => {
            this.cloudSpawnEffect.style.animation = 'cloudSpawn 1.5s ease-out';
        }, 2000);

        // Add new server instances
        setTimeout(() => {
            this.addServerInstances(3);
        }, 3000);

        setTimeout(() => {
            this.addServerInstances(3);
        }, 5000);

        // Update metrics to critical then improving
        this.animateMetrics({ cpu: 95, memory: 90, network: 85 }, 2000);
        setTimeout(() => {
            this.animateMetrics({ cpu: 60, memory: 65, network: 55 }, 4000);
        }, 4000);
    }

    triggerLoadDistribution() {
        this.phaseText.textContent = 'Load Distributed & Stabilized';

        // Stabilize user count
        this.animateUserGrowth(800, 600, 5000);

        // Distribute load across all servers
        this.serverInstances.forEach((server, index) => {
            if (server.classList.contains('active')) {
                const utilizationBar = server.querySelector('.utilization-bar');
                setTimeout(() => {
                    utilizationBar.style.width = `${30 + Math.random() * 25}%`;
                }, index * 200);
            }
        });

        // Remove scaling trigger
        setTimeout(() => {
            this.scalingTrigger.classList.remove('active', 'critical');
        }, 2000);

        // Stabilize load balancer
        setTimeout(() => {
            this.loadBalancer.style.animation = 'systemStabilized 3s infinite';
        }, 3000);

        // Final stable metrics
        this.animateMetrics({ cpu: 35, memory: 45, network: 30 }, 6000);

        // Show metrics dashboard
        setTimeout(() => {
            this.metricsDashboard.classList.add('visible');
        }, 4000);
    }

    animateUserGrowth(from, to, duration) {
        const startTime = Date.now();
        const startCount = from;
        const endCount = to;

        const updateUsers = () => {
            if (!this.isPlaying) return;

            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const currentCount = Math.floor(startCount + (endCount - startCount) * progress);

            this.userCount = currentCount;
            this.updateUserDisplay();

            if (progress < 1) {
                requestAnimationFrame(updateUsers);
            }
        };

        updateUsers();
    }

    updateUserDisplay() {
        this.userCountDisplay.textContent = this.userCount.toLocaleString();

        // Update user icons
        const visibleUsers = Math.min(this.userCount, 64);
        this.userIcons.forEach((icon, index) => {
            if (index < visibleUsers) {
                icon.classList.add('active');

                // Color coding based on load
                icon.classList.remove('warning', 'critical');
                if (this.userCount > 500) {
                    icon.classList.add('critical');
                } else if (this.userCount > 200) {
                    icon.classList.add('warning');
                }

                // Staggered animation
                setTimeout(() => {
                    if (icon.classList.contains('active')) {
                        icon.style.animationDelay = `${index * 50}ms`;
                    }
                }, index * 20);
            } else {
                icon.classList.remove('active', 'warning', 'critical');
            }
        });
    }

    addServerInstances(count) {
        let added = 0;
        this.serverInstances.forEach((server, index) => {
            if (!server.classList.contains('active') && added < count) {
                setTimeout(() => {
                    server.classList.add('active', 'scaling');
                    server.querySelector('.utilization-bar').style.width = `${20 + Math.random() * 30}%`;

                    // Remove scaling class after animation
                    setTimeout(() => {
                        server.classList.remove('scaling');
                    }, 800);
                }, added * 400);
                added++;
            }
        });
        this.serverCount += added;
    }

    animateMetrics(targetMetrics, duration) {
        const startTime = Date.now();
        const startMetrics = { ...this.currentUtilization };

        const updateMetrics = () => {
            if (!this.isPlaying) return;

            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);

            Object.keys(targetMetrics).forEach(key => {
                const startValue = startMetrics[key];
                const endValue = targetMetrics[key];
                const currentValue = Math.floor(startValue + (endValue - startValue) * progress);
                this.currentUtilization[key] = currentValue;
            });

            this.updateMetricsDisplay();

            if (progress < 1) {
                requestAnimationFrame(updateMetrics);
            }
        };

        updateMetrics();
    }

    updateMetricsDisplay() {
        const metrics = ['cpu', 'memory', 'network'];
        const values = [this.currentUtilization.cpu, this.currentUtilization.memory, this.currentUtilization.network];

        this.metricFills.forEach((fill, index) => {
            fill.style.width = `${values[index]}%`;
        });

        this.metricValues.forEach((value, index) => {
            value.textContent = `${values[index]}%`;
        });
    }

    adjustUserLoad(newUserCount) {
        this.userCount = newUserCount;
        this.updateUserDisplay();

        // Adjust server utilization based on user load
        const baseUtilization = Math.min(newUserCount / 10, 90);
        this.serverInstances.forEach((server, index) => {
            if (server.classList.contains('active')) {
                const utilizationBar = server.querySelector('.utilization-bar');
                const randomVariation = Math.random() * 20 - 10;
                utilizationBar.style.width = `${Math.max(10, Math.min(95, baseUtilization + randomVariation))}%`;
            }
        });

        // Update metrics based on load
        const cpuLoad = Math.min(30 + newUserCount / 15, 95);
        const memoryLoad = Math.min(40 + newUserCount / 20, 90);
        const networkLoad = Math.min(25 + newUserCount / 25, 85);

        this.currentUtilization = { cpu: cpuLoad, memory: memoryLoad, network: networkLoad };
        this.updateMetricsDisplay();

        // Show scaling trigger if load is high
        if (newUserCount > 300) {
            this.scalingTrigger.classList.add('active');
            if (newUserCount > 600) {
                this.scalingTrigger.classList.add('critical');
            }
        } else {
            this.scalingTrigger.classList.remove('active', 'critical');
        }
    }

    onServerClick(serverIndex) {
        const server = this.serverInstances[serverIndex];
        const isActive = server.classList.contains('active');
        const utilization = server.querySelector('.utilization-bar').style.width;

        const serverInfo = {
            id: `server-${serverIndex + 1}`,
            status: isActive ? 'Active' : 'Inactive',
            utilization: isActive ? utilization : '0%',
            connections: isActive ? Math.floor(Math.random() * 500 + 100) : 0,
            uptime: isActive ? `${Math.floor(Math.random() * 24)}h ${Math.floor(Math.random() * 60)}m` : '0h 0m'
        };

        console.log('Server Details:', serverInfo);

        // Visual feedback
        server.style.transform += ' scale(0.95)';
        setTimeout(() => {
            server.style.transform = server.style.transform.replace(' scale(0.95)', '');
        }, 150);
    }

    onLoadBalancerClick() {
        const lbInfo = {
            totalConnections: this.userCount,
            activeServers: this.serverCount,
            requestsPerSecond: Math.floor(this.userCount * 2.5),
            averageResponseTime: `${Math.floor(Math.random() * 100 + 50)}ms`,
            algorithm: 'Round Robin with Health Checks'
        };

        console.log('Load Balancer Status:', lbInfo);

        // Visual feedback
        this.loadBalancer.style.transform += ' scale(0.95)';
        setTimeout(() => {
            this.loadBalancer.style.transform = this.loadBalancer.style.transform.replace(' scale(0.95)', '');
        }, 150);
    }

    updateProgressBar() {
        if (!this.isPlaying) return;

        const startTime = Date.now();
        const updateProgress = () => {
            if (!this.isPlaying) return;

            const elapsed = Date.now() - startTime;
            const progress = (elapsed % this.totalDuration) / this.totalDuration;
            this.progressBar.style.width = (progress * 100) + '%';

            requestAnimationFrame(updateProgress);
        };

        updateProgress();
    }

    resetAnimation() {
        // Reset user display
        this.userCount = 10;
        this.updateUserDisplay();

        // Reset servers
        this.serverInstances.forEach((server, index) => {
            if (index >= 3) {
                server.classList.remove('active', 'scaling');
            }
            server.querySelector('.utilization-bar').style.width = `${20 + Math.random() * 30}%`;
        });

        // Reset metrics
        this.currentUtilization = { cpu: 30, memory: 40, network: 25 };
        this.updateMetricsDisplay();

        // Reset UI elements
        this.scalingTrigger.classList.remove('active', 'critical');
        this.metricsDashboard.classList.remove('visible');
        this.loadBalancer.style.animation = '';
        this.progressBar.style.width = '0%';
        this.userLoadSlider.value = '10';

        // Reset traffic flows
        this.trafficFlows.forEach(flow => {
            flow.style.opacity = '0';
        });
    }

    showInfo() {
        const infoText = `
Auto-Scaling Chat System Animation

Animation Phases:
1. Initial Load (0-8.75s): Users connect, normal resource usage
2. Resource Optimization (8.75-17.5s): Load increases, system optimizes
3. Auto-Scaling Triggered (17.5-26.25s): Threshold reached, new servers spawn
4. Load Distribution (26.25-35s): Load balanced, system stabilized

Interactive Features:
- Adjust user load slider to trigger different scaling scenarios
- Click on servers to view detailed metrics
- Click on load balancer for status information
- Hover over animation for enhanced effects

This demonstrates SAGE's high resource utilization capabilities through cloud infrastructure scaling visualization.
        `;

        alert(infoText);
    }

    onHover() {
        this.container.classList.add('hovered');
        this.metricsDashboard.classList.add('visible');
    }

    onHoverEnd() {
        this.container.classList.remove('hovered');
        if (!this.isPlaying || this.currentPhase < 3) {
            this.metricsDashboard.classList.remove('visible');
        }
    }

    destroy() {
        this.pause();
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Initialize Auto-Scaling Animation when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Create animation container if it doesn't exist
    const existingContainer = document.getElementById('autoScalingAnimation');
    if (!existingContainer) {
        console.log('Auto-scaling animation container not found. Will be created when HTML structure is added.');
    } else {
        // Initialize the animation
        window.autoScalingAnimation = new AutoScalingAnimation('autoScalingAnimation');
    }
});

// Function to initialize auto-scaling animation (can be called from HTML)
function initializeAutoScaling(containerId = 'autoScalingAnimation') {
    if (window.autoScalingAnimation) {
        window.autoScalingAnimation.destroy();
    }
    window.autoScalingAnimation = new AutoScalingAnimation(containerId);
}

// Pipeline Connection Lines - 修复版本
function updateConnectionLines() {
    const svg = document.querySelector('.connection-svg');
    if (!svg) return;

    const container = document.querySelector('.pipeline-building-content');
    if (!container) return;

    // 获取所有需要的元素
    const step1 = document.getElementById('step-1');
    const step2 = document.getElementById('step-2');
    const step3 = document.getElementById('step-3');

    // 确保获取正确的pipeline节点
    const queryInput = document.getElementById('query-input');
    const vectorSearch = document.getElementById('vector-search');
    const arrow2 = document.getElementById('arrow-2');

    // 验证元素获取是否正确
    if (queryInput && !queryInput.textContent.includes('问题输入')) {
        console.error('queryInput元素获取错误!', queryInput.textContent);
    }
    if (vectorSearch && !vectorSearch.textContent.includes('向量检索')) {
        console.error('vectorSearch元素获取错误!', vectorSearch.textContent);
    }



    if (!step1 || !step2 || !step3 || !queryInput || !vectorSearch || !arrow2) return;

    // 精确计算连接点，支持移动端768px以下的水平布局
    function getConnectionPoints(sourceElement, targetElement, gap = 8) {
        const sourceRect = sourceElement.getBoundingClientRect();
        const targetRect = targetElement.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();

        // 转换为相对坐标
        const sourceBox = {
            left: sourceRect.left - containerRect.left,
            top: sourceRect.top - containerRect.top,
            right: sourceRect.right - containerRect.left,
            bottom: sourceRect.bottom - containerRect.top,
            centerX: sourceRect.left - containerRect.left + sourceRect.width / 2,
            centerY: sourceRect.top - containerRect.top + sourceRect.height / 2
        };

        const targetBox = {
            left: targetRect.left - containerRect.left,
            top: targetRect.top - containerRect.top,
            right: targetRect.right - containerRect.left,
            bottom: targetRect.bottom - containerRect.top,
            centerX: targetRect.left - containerRect.left + targetRect.width / 2,
            centerY: targetRect.top - containerRect.top + targetRect.height / 2
        };

        let fromPoint, toPoint;

        // 检测是否为移动端布局 (768px以下)
        const isMobile = window.innerWidth <= 768;
        const isVerySmallScreen = window.innerWidth <= 480;

        if (isMobile) {
            // 移动端水平布局：step-1,step-2在左侧，step-3,step-4在右侧，pipeline在中央
            // 调试信息
            console.log(`Connection: ${sourceElement.id} -> ${targetElement.id}, screen width: ${window.innerWidth}`);

            if (sourceElement.id === 'step-1' || sourceElement.id === 'step-2') {
                console.log(`调试 ${sourceElement.id}: sourceBox.centerX=${sourceBox.centerX}, targetBox.centerX=${targetBox.centerX}`);
                console.log(`sourceBox: left=${sourceBox.left}, right=${sourceBox.right}`);
                console.log(`targetBox: left=${targetBox.left}, right=${targetBox.right}`);

                // 用户要求："上端朝右，下端朝左"
                // 这意味着视觉上连接线应该从右边出发，向左边方向延伸

                // 正确的连接：从左侧step的右边连接到中央pipeline的左边
                // 这样连接线从左向右流动，符合"上端朝右"的视觉效果
                fromPoint = { x: sourceBox.right + gap, y: sourceBox.centerY };
                toPoint = { x: targetBox.left - gap, y: targetBox.centerY };
                console.log(`正确连接: 从step右边到pipeline左边`);
                console.log(`步骤 ${sourceElement.id}: from(${fromPoint.x}, ${fromPoint.y}) to(${toPoint.x}, ${toPoint.y})`);
            } else if (sourceElement.id === 'step-3') {
                // step-3在右侧连接到中央pipeline：从左边框中部连接到右边框中部
                // step-3: 橙色线上端朝左，下端朝右
                fromPoint = { x: sourceBox.left - gap, y: sourceBox.centerY };
                toPoint = { x: targetBox.right + gap, y: targetBox.centerY };
                console.log(`右侧步骤 ${sourceElement.id}: from(${fromPoint.x}, ${fromPoint.y}) to(${toPoint.x}, ${toPoint.y})`);
            } else if (sourceElement.id === 'step-4') {
                // step-4连接到箭头，特殊处理
                if (targetElement.id === 'arrow-2') {
                    // step-4在右侧连接到箭头：从左边框中部连接到箭头左侧
                    fromPoint = { x: sourceBox.left - gap, y: sourceBox.centerY };
                    toPoint = { x: targetBox.left - gap, y: targetBox.centerY };
                } else {
                    // 其他情况，右侧步骤连接到中央pipeline
                    fromPoint = { x: sourceBox.left - gap, y: sourceBox.centerY };
                    toPoint = { x: targetBox.right + gap, y: targetBox.centerY };
                }
                console.log(`右侧步骤 ${sourceElement.id}: from(${fromPoint.x}, ${fromPoint.y}) to(${toPoint.x}, ${toPoint.y})`);
            } else {
                // 默认水平连接，考虑更精确的定位
                if (targetBox.centerX > sourceBox.centerX) {
                    fromPoint = { x: sourceBox.right + gap, y: sourceBox.centerY };
                    toPoint = { x: targetBox.left - gap, y: targetBox.centerY };
                } else {
                    fromPoint = { x: sourceBox.left - gap, y: sourceBox.centerY };
                    toPoint = { x: targetBox.right + gap, y: targetBox.centerY };
                }
                console.log(`默认连接: from(${fromPoint.x}, ${fromPoint.y}) to(${toPoint.x}, ${toPoint.y})`);
            }
        } else {
            // 桌面端垂直布局：按照原有逻辑
            if (targetBox.centerY > sourceBox.centerY) {
                // 目标在下方：从源元素底部连接到目标元素顶部
                fromPoint = { x: sourceBox.centerX, y: sourceBox.bottom + gap };
                toPoint = { x: targetBox.centerX, y: targetBox.top - gap };
            } else if (targetBox.centerY < sourceBox.centerY) {
                // 目标在上方：从源元素顶部连接到目标元素底部
                fromPoint = { x: sourceBox.centerX, y: sourceBox.top - gap };
                toPoint = { x: targetBox.centerX, y: targetBox.bottom + gap };
            } else {
                // 同一水平线：水平连接
                if (targetBox.centerX > sourceBox.centerX) {
                    fromPoint = { x: sourceBox.right + gap, y: sourceBox.centerY };
                    toPoint = { x: targetBox.left - gap, y: targetBox.centerY };
                } else {
                    fromPoint = { x: sourceBox.left - gap, y: sourceBox.centerY };
                    toPoint = { x: targetBox.right + gap, y: targetBox.centerY };
                }
            }
        }

        return { from: fromPoint, to: toPoint };
    }

    // 创建带圆角的路径，支持移动端和桌面端不同布局
    function createRoundedPath(fromPoint, toPoint) {
        const dx = toPoint.x - fromPoint.x;
        const dy = toPoint.y - fromPoint.y;
        const isMobile = window.innerWidth <= 768;
        const isVerySmallScreen = window.innerWidth <= 480;

        // 如果距离太小，直接画直线
        if (Math.abs(dx) < 10 && Math.abs(dy) < 10) {
            return `M ${fromPoint.x},${fromPoint.y} L ${toPoint.x},${toPoint.y}`;
        }

        if (isMobile && Math.abs(dy) < 20) {
            // 移动端水平连接：如果垂直距离很小，画直线或简单的水平线
            return `M ${fromPoint.x},${fromPoint.y} L ${toPoint.x},${toPoint.y}`;
        }

        // 动态计算圆角半径
        const maxRadius = Math.min(Math.abs(dx) / 3, Math.abs(dy) / 6, 8);
        const radius = Math.max(3, maxRadius);

        if (isMobile) {
            // 移动端：主要是水平连接，可能需要垂直调整
            if (Math.abs(dy) < radius * 2) {
                // 几乎在同一水平线上，画直线
                return `M ${fromPoint.x},${fromPoint.y} L ${toPoint.x},${toPoint.y}`;
            } else {
                // 需要垂直调整的水平连接
                const midX = fromPoint.x + dx / 2;
                const actualRadius = Math.min(radius, Math.abs(dx) / 4, Math.abs(dy) / 4);

                if (actualRadius < 2) {
                    return `M ${fromPoint.x},${fromPoint.y} L ${midX},${fromPoint.y} L ${midX},${toPoint.y} L ${toPoint.x},${toPoint.y}`;
                }

                const directionX = dx > 0 ? 1 : -1;
                const directionY = dy > 0 ? 1 : -1;

                return `M ${fromPoint.x},${fromPoint.y} ` +
                       `L ${midX - directionX * actualRadius},${fromPoint.y} ` +
                       `Q ${midX},${fromPoint.y} ${midX},${fromPoint.y + directionY * actualRadius} ` +
                       `L ${midX},${toPoint.y - directionY * actualRadius} ` +
                       `Q ${midX},${toPoint.y} ${midX + directionX * actualRadius},${toPoint.y} ` +
                       `L ${toPoint.x},${toPoint.y}`;
            }
        } else {
            // 桌面端：主要是垂直连接
            if (Math.abs(dx) < radius * 2) {
                return `M ${fromPoint.x},${fromPoint.y} L ${toPoint.x},${toPoint.y}`;
            }

            const midY = fromPoint.y + dy / 2;
            const direction = dx > 0 ? 1 : -1;
            const verticalLength1 = Math.abs(midY - fromPoint.y);
            const verticalLength2 = Math.abs(toPoint.y - midY);
            const actualRadius = Math.min(radius, verticalLength1 - 1, verticalLength2 - 1);

            if (actualRadius < 2) {
                return `M ${fromPoint.x},${fromPoint.y} L ${fromPoint.x},${midY} L ${toPoint.x},${midY} L ${toPoint.x},${toPoint.y}`;
            }

            const corner1Y = fromPoint.y < toPoint.y ? midY - actualRadius : midY + actualRadius;
            const corner2Y = fromPoint.y < toPoint.y ? midY + actualRadius : midY - actualRadius;

            return `M ${fromPoint.x},${fromPoint.y} ` +
                   `L ${fromPoint.x},${corner1Y} ` +
                   `Q ${fromPoint.x},${midY} ${fromPoint.x + direction * actualRadius},${midY} ` +
                   `L ${toPoint.x - direction * actualRadius},${midY} ` +
                   `Q ${toPoint.x},${midY} ${toPoint.x},${corner2Y} ` +
                   `L ${toPoint.x},${toPoint.y}`;
        }
    }

    // 更新三条连接线
    const line1 = document.getElementById('line1');
    const line2 = document.getElementById('line2');
    const line3 = document.getElementById('line3');

    if (line1) {
        // 获取数据源 -> 问题输入（确保连接到正确的元素）
        const actualQueryInput = document.querySelector('.pipeline-node[id="query-input"]') ||
                                document.querySelector('.pipeline-node:first-of-type');
        const points = getConnectionPoints(step1, actualQueryInput, 10);
        line1.setAttribute('d', createRoundedPath(points.from, points.to));
        line1.setAttribute('stroke', '#3b82f6');
    }

    if (line2) {
        // 编码算子 -> 向量检索（确保连接到正确的元素）
        const actualVectorSearch = document.querySelector('.pipeline-node[id="vector-search"]') ||
                                  document.querySelector('.pipeline-node:nth-of-type(3)');
        const points = getConnectionPoints(step2, actualVectorSearch, 10);
        line2.setAttribute('d', createRoundedPath(points.from, points.to));
        line2.setAttribute('stroke', '#10b981');
    }

    if (line3) {
        // step-3 (组装Pipeline) -> arrow-2 (在提问重构和向量检索之间的箭头)
        const points = getConnectionPoints(step3, arrow2, 10);
        line3.setAttribute('d', createRoundedPath(points.from, points.to));
        line3.setAttribute('stroke', '#f59e0b');
    }

    // 检查是否需要处理step-4的连接
    // step-4通常连接到pipeline的结果输出或执行部分
    const step4 = document.getElementById('step-4');
    const resultOutput = document.getElementById('result-output');
    if (step4 && resultOutput) {
        // 如果有额外的连接线用于step-4，可以在这里添加
        // 目前根据HTML结构，只有3条连接线
        console.log('Step-4 positioned but no dedicated connection line in current design');
    }
}

// 调试函数
function debugElements() {
    console.log('=== 元素调试信息 ===');
    const nodes = document.querySelectorAll('.pipeline-node');
    nodes.forEach((node, index) => {
        console.log(`节点 ${index}: ${node.id} - ${node.textContent.trim()}`);
    });

    const queryInput = document.getElementById('query-input');
    const vectorSearch = document.getElementById('vector-search');
    console.log('queryInput:', queryInput ? queryInput.textContent.trim() : 'NOT FOUND');
    console.log('vectorSearch:', vectorSearch ? vectorSearch.textContent.trim() : 'NOT FOUND');
}

// 当页面加载和窗口大小改变时更新连接线
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        debugElements();
        updateConnectionLines();
    }, 500); // 延迟执行确保DOM完全加载
});

window.addEventListener('resize', function() {
    setTimeout(updateConnectionLines, 100);
});

// 监听滚动事件，因为可能影响元素位置
window.addEventListener('scroll', function() {
    updateConnectionLines();
});
