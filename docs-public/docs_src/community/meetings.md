# Intellistream 周会安排

<div id="weekly-schedule-container">
    <div class="controls">
        <!-- <button id="config-btn" onclick="scheduler.showConfig()">配置 Gist</button> -->
        <button id="token-btn" onclick="scheduler.showTokenConfig()">设置密钥</button>
        <button id="reset-all" onclick="scheduler.resetAll()">重置所有</button>
        <button id="sync-data" onclick="scheduler.syncWithCloud()">同步数据</button>
        <div class="sync-status" id="sync-status">未同步</div>
    </div>

```
<!-- Token 配置弹窗 -->
<div id="token-config-modal" class="modal" style="display: none;">
    <div class="modal-content">
        <div class="modal-header">
            <h3>🔑 配置 GitHub Token</h3>
            <span class="close" onclick="scheduler.hideTokenConfig()">&times;</span>
        </div>
        <div class="modal-body">
            <p><strong>⚠️ 重要安全说明</strong></p>
            <p>为了防止 Token 被 GitHub 自动撤销，此系统采用安全配置方式：</p>
            <div class="form-group">
                <label for="gist-token">GitHub Token:</label>
                <input type="password" id="gist-token" placeholder="ghp_xxxxxxxxxxxxxxxxxxxx" style="width: 100%; padding: 8px; margin: 5px 0;">
                <small>⚠️ Token 只在当前浏览器会话中保存，页面刷新后需要重新输入</small>
            </div>
            <div class="form-actions">
                <button onclick="scheduler.setGistToken()" class="primary-btn">设置 Token</button>
                <button onclick="scheduler.hideTokenConfig()" class="secondary-btn">取消</button>
            </div>
            <div class="help-section">
                <h4>如何获取 GitHub Token？</h4>
                <ol>
                    <li>访问 GitHub Settings → Developer settings → Personal access tokens</li>
                    <li>点击 "Generate new token (classic)"</li>
                    <li>只勾选 "gist" 权限</li>
                    <li>复制生成的 Token</li>
                </ol>
                <p><strong>注意</strong>：此安全设计避免了 Token 被意外提交到代码库而被撤销。</p>
            </div>
        </div>
    </div>
</div>

<!-- 周期信息显示 -->
<div class="cycle-info">
    <span>当前周期: <strong id="current-cycle">1</strong></span>
    <span>本周日期: <strong id="current-week-date">加载中...</strong></span>
    <span>最后同步: <strong id="last-sync">从未</strong></span>
</div>

<!-- 上方两个区域 - 并排显示 -->
<div class="presenters-sections">
    <div class="presenters-column">
        <h3>本周汇报人员</h3>
        <div id="current-presenters" class="drop-zone current-week-zone">
            <div class="zone-hint">本周汇报人员</div>
        </div>
    </div>

    <div class="presenters-column">
        <h3>下周准备汇报人员</h3>
        <div id="next-presenters" class="drop-zone next-week-zone">
            <div class="zone-hint">下周准备汇报人员</div>
        </div>
    </div>
</div>

<!-- 下方两个区域 - 并排显示 -->
<div class="members-sections">
    <div class="members-column">
        <h3>已汇报成员 (本周期)</h3>
        <div id="presented-members" class="drop-zone presented-zone">
            <div class="zone-hint">已汇报的成员</div>
        </div>
    </div>

    <div class="members-column">
        <h3>待汇报成员</h3>
        <div id="pending-members" class="drop-zone pending-zone">
            <div class="zone-hint">待汇报的成员</div>
        </div>
    </div>
</div>
```

</div>

<style>
#weekly-schedule-container {
    max-width: 1200px;
    margin: 20px auto;
    padding: 20px;
    font-family: 'Public Sans', sans-serif;
    background: #f8f9fa;
    border-radius: 12px;
}

.controls-section {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 30px;
    padding: 15px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.controls {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    padding: 15px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    justify-content: flex-start;
    align-items: center;
}

.controls button {
    padding: 10px 16px;
    background: #007acc;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.2s ease;
}

.controls button:hover {
    background: #005a9e;
    transform: translateY(-1px);
}

.sync-status {
    margin-left: auto;
    padding: 5px 10px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
}

.sync-status.synced {
    background: #e8f5e8;
    color: #2e7d32;
}

.sync-status.syncing {
    background: #fff3e0;
    color: #f57c00;
}

.sync-status.error {
    background: #ffebee;
    color: #d32f2f;
}

.cycle-info {
    display: flex;
    gap: 20px;
    color: #666;
    font-size: 14px;
    margin-bottom: 20px;
}

.cycle-info span {
    padding: 5px 10px;
    background: #e3f2fd;
    border-radius: 4px;
}

/* 上方两个区域 - 并排显示 */
.presenters-sections {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 30px;
}

.presenters-column h3 {
    margin-bottom: 15px;
    color: #333;
    font-size: 16px;
}

.current-week-zone {
    min-height: 180px;
    background: linear-gradient(135deg, #e8f5e8, #f1f8e9);
    border: 3px dashed #4caf50;
    border-radius: 12px;
    position: relative;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    padding: 20px;
    align-items: flex-start;
    align-content: flex-start;
}

.next-week-zone {
    min-height: 180px;
    background: linear-gradient(135deg, #e1f5fe, #f3e5f5);
    border: 3px dashed #00bcd4;
    border-radius: 12px;
    position: relative;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    padding: 20px;
    align-items: flex-start;
    align-content: flex-start;
}

/* 下方两个区域 */
.members-sections {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
}

.members-column h3 {
    margin-bottom: 15px;
    color: #333;
    font-size: 16px;
}

.presented-zone {
    min-height: 300px;
    background: linear-gradient(135deg, #fff3e0, #fef7ed);
    border: 2px dashed #ff9800;
    border-radius: 8px;
    padding: 15px;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: flex-start;
    align-content: flex-start;
}

.pending-zone {
    min-height: 300px;
    background: linear-gradient(135deg, #e3f2fd, #f3e5f5);
    border: 2px dashed #2196f3;
    border-radius: 8px;
    padding: 15px;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: flex-start;
    align-content: flex-start;
}

.drop-zone {
    transition: all 0.3s ease;
    position: relative;
}

.drop-zone.drag-over {
    transform: scale(1.02);
    box-shadow: 0 8px 16px rgba(0,0,0,0.15);
}

.current-week-zone.drag-over {
    border-color: #2e7d32;
    background: linear-gradient(135deg, #c8e6c9, #dcedc8);
}

.next-week-zone.drag-over {
    border-color: #0097a7;
    background: linear-gradient(135deg, #b2ebf2, #e1bee7);
}

.presented-zone.drag-over {
    border-color: #f57c00;
    background: linear-gradient(135deg, #ffe0b2, #fff3e0);
}

.pending-zone.drag-over {
    border-color: #1976d2;
    background: linear-gradient(135deg, #bbdefb, #e1bee7);
}

.zone-hint {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    color: #999;
    font-style: italic;
    font-size: 14px;
    pointer-events: none;
    opacity: 0.7;
}

.zone-hint.hidden {
    display: none;
}

.current-week-zone .zone-hint {
    color: #4caf50;
}

.next-week-zone .zone-hint {
    color: #00bcd4;
}

/* 成员卡片样式 */
.member-card {
    background: white;
    padding: 12px 16px;
    border-radius: 8px;
    cursor: grab;
    user-select: none;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 120px;
    position: relative;
}

.member-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.member-card.dragging {
    opacity: 0.8;
    transform: rotate(5deg);
    cursor: grabbing;
    z-index: 1000;
}

.member-card .name {
    font-weight: 500;
    color: #333;
}

.member-card .status {
    font-size: 10px;
    padding: 2px 6px;
    border-radius: 10px;
    color: white;
    font-weight: 500;
}

.member-card .status.current {
    background: #4caf50;
}

.member-card .status.next {
    background: #00bcd4;
}

.member-card .status.presented {
    background: #ff9800;
}

.member-card .status.pending {
    background: #2196f3;
}

.member-card .last-date {
    font-size: 11px;
    color: #666;
    margin-left: auto;
}

/* 响应式设计 */
@media (max-width: 768px) {
    .controls-section {
        flex-direction: column;
        gap: 15px;
        align-items: stretch;
    }

    .controls {
        flex-direction: column;
        align-items: stretch;
    }

    .cycle-info {
        flex-direction: column;
        gap: 10px;
    }

    .presenters-sections,
    .members-sections {
        grid-template-columns: 1fr;
        gap: 15px;
    }

    .current-week-zone,
    .next-week-zone {
        min-height: 100px;
        padding: 15px;
    }

    .presented-zone,
    .pending-zone {
        min-height: 150px;
    }
}

/* 动画效果 */
@keyframes memberDrop {
    0% { transform: scale(1.1); }
    100% { transform: scale(1); }
}

.member-card.dropped {
    animation: memberDrop 0.3s ease;
}

/* 空状态样式 */
.empty-zone .zone-hint {
    opacity: 1;
}

.non-empty-zone .zone-hint {
    display: none;
}

/* 弹窗样式 */
.modal {
    display: none;
    position: fixed;
    z-index: 1000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
}

.modal-content {
    background-color: white;
    margin: 5% auto;
    padding: 0;
    border-radius: 8px;
    width: 90%;
    max-width: 600px;
    max-height: 80vh;
    overflow-y: auto;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px;
    border-bottom: 1px solid #eee;
    background-color: #f8f9fa;
    border-radius: 8px 8px 0 0;
}

.modal-header h3 {
    margin: 0;
    color: #333;
}

.close {
    color: #aaa;
    font-size: 28px;
    font-weight: bold;
    cursor: pointer;
    line-height: 1;
}

.close:hover {
    color: #333;
}

.modal-body {
    padding: 20px;
}

.form-group {
    margin-bottom: 20px;
}

.form-group label {
    display: block;
    margin-bottom: 8px;
    font-weight: 600;
    color: #333;
}

.form-actions {
    display: flex;
    gap: 10px;
    margin: 20px 0;
}

.primary-btn {
    background: #007acc;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 5px;
    cursor: pointer;
    font-weight: 500;
}

.primary-btn:hover {
    background: #005a9e;
}

.secondary-btn {
    background: #6c757d;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 5px;
    cursor: pointer;
    font-weight: 500;
}

.secondary-btn:hover {
    background: #545b62;
}

.help-section {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 5px;
    margin-top: 20px;
}

.help-section h4 {
    margin-top: 0;
    color: #333;
}

.help-section ol {
    margin: 10px 0;
    padding-left: 20px;
}

.help-section li {
    margin: 5px 0;
}
</style>

<script src="../../assets/js/runtime-config.js"></script>

<script>
// 运行时配置支持
window.SAGE_RUNTIME_CONFIG = window.SAGE_RUNTIME_CONFIG || {
    gistToken: '' // 从环境变量注入，或用户手动配置
};

class CloudSyncScheduler {
    constructor() {
        // GitHub Gist 配置
        this.GITHUB_CONFIG = {
            gistId: 'b7b18befbd332c97f938e7859df5f7ef', // 您的 Gist ID
            token: window.SAGE_RUNTIME_CONFIG?.gistToken || '', // 从运行时配置或环境变量获取
            filename: 'schedule_data.json'
        };

        // 尝试从 localStorage 加载配置（作为后备方案）
        this.loadConfig();

        // 如果仍然没有 token，在控制台提示
        if (!this.GITHUB_CONFIG.token) {
            console.warn('🔑 未检测到 GitHub Token，读取功能正常，写入功能需要配置 Token');
        }

        // 数据键名
        this.STORAGE_KEY = 'weekly_schedule_data';

        // 初始化数据
        this.members = [];
        this.currentCycle = 1;
        this.weekHistory = [];
        this.currentWeekPresenters = [];
        this.nextWeekPresenters = [];
        this.lastSync = null;

        this.init();
    }

    async init() {
        this.updateSyncStatus('syncing', '正在加载数据...');

        try {
            // 尝试从云端加载数据
            await this.loadFromCloud();
            this.updateSyncStatus('synced', '数据已同步');
        } catch (error) {
            console.warn('云端加载失败，使用本地数据:', error);
            // 回退到本地存储
            this.loadFromLocal();
            this.updateSyncStatus('error', '云端同步失败');
        }

        this.updateCycleInfo();
        this.initializeSchedule();
        this.renderMembers();
        this.setupDragAndDrop();

        // 设置自动同步
        this.setupAutoSync();
    }

    async loadFromCloud() {
        try {
            const response = await this.fetchFromGist();
            if (response && response.data) {
                this.loadData(response.data);
                this.lastSync = new Date().toISOString();
                return;
            }
        } catch (error) {
            console.warn('Gist 加载失败:', error);
        }

        // 如果加载失败，抛出错误回退到本地
        throw new Error('Gist 加载失败');
    }

    async fetchFromGist() {
        const { gistId, filename } = this.GITHUB_CONFIG;

        if (!gistId || gistId === '1234567890abcdef') {
            throw new Error('请先配置有效的 Gist ID');
        }

        // 构建请求选项，如果有 token 就添加认证头
        const fetchOptions = {
            method: 'GET',
            headers: {
                'Accept': 'application/vnd.github.v3+json'
            }
        };

        // 添加认证头（如果有 token）
        const token = this.GITHUB_CONFIG.token || window.SAGE_RUNTIME_CONFIG?.gistToken;
        if (token) {
            fetchOptions.headers['Authorization'] = `token ${token}`;
        }

        const response = await fetch(`https://api.github.com/gists/${gistId}`, fetchOptions);

        if (!response.ok) {
            throw new Error(`Gist 请求失败: ${response.status}`);
        }

        const gist = await response.json();
        const content = gist.files[filename]?.content;

        if (content) {
            try {
                return { data: JSON.parse(content) };
            } catch (parseError) {
                throw new Error('Gist 数据格式错误');
            }
        }

        return null;
    }

    async fetchFromIssueComment() {
        // 移除这个方法，只使用 Gist
        throw new Error('已弃用，仅使用 Gist 方案');
    }

    loadFromLocal() {
        const storedData = localStorage.getItem(this.STORAGE_KEY);
        if (storedData) {
            try {
                this.loadData(JSON.parse(storedData));
            } catch (error) {
                console.error('本地数据解析失败:', error);
                this.loadDefaultData();
            }
        } else {
            this.loadDefaultData();
        }
    }

    loadData(data) {
        this.members = data.members || this.getDefaultMembers();
        this.currentCycle = data.currentCycle || 1;
        this.weekHistory = data.weekHistory || [];
        this.currentWeekPresenters = data.currentWeekPresenters || [];
        this.nextWeekPresenters = data.nextWeekPresenters || [];
        this.lastSync = data.lastSync || null;
    }

    loadDefaultData() {
        this.members = this.getDefaultMembers();
        this.currentCycle = 1;
        this.weekHistory = [];
        this.currentWeekPresenters = [];
        this.nextWeekPresenters = [];
        this.lastSync = null;
    }

    getDefaultMembers() {
        return [
            { id: 1, name: 'Hongru', lastPresented: null, cycleCount: 0 },
            { id: 2, name: 'Mingqi', lastPresented: null, cycleCount: 0 },
            { id: 3, name: 'Ruicheng', lastPresented: null, cycleCount: 0 },
            { id: 4, name: 'Ruipeng', lastPresented: null, cycleCount: 0 },
            { id: 5, name: 'Xinyan', lastPresented: null, cycleCount: 0 },
            { id: 6, name: 'Ziao', lastPresented: null, cycleCount: 0 },
            { id: 7, name: 'Senlei', lastPresented: null, cycleCount: 0 },
            { id: 8, name: 'Xincai', lastPresented: null, cycleCount: 0 },
            { id: 9, name: 'Liujun', lastPresented: null, cycleCount: 0 },
            { id: 10, name: 'Yanbo', lastPresented: null, cycleCount: 0 },
            { id: 11, name: 'Jinyun', lastPresented: null, cycleCount: 0 },
            { id: 12, name: 'Jingyuan', lastPresented: null, cycleCount: 0 },
            { id: 13, name: 'Peilin', lastPresented: null, cycleCount: 0 },
            { id: 14, name: 'Xiaohan', lastPresented: null, cycleCount: 0 },
            { id: 15, name: 'Changwu', lastPresented: null, cycleCount: 0 }
        ];
    }

    exportData() {
        return {
            members: this.members,
            currentCycle: this.currentCycle,
            weekHistory: this.weekHistory,
            currentWeekPresenters: this.currentWeekPresenters,
            nextWeekPresenters: this.nextWeekPresenters,
            lastSync: new Date().toISOString(),
            version: '2.0'
        };
    }

    async saveToCloud() {
        const data = this.exportData();

        try {
            this.updateSyncStatus('syncing', '正在同步到云端...');

            // 保存到本地作为备份
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(data));

            // 保存到 Gist
            await this.saveToGist(data);

            this.lastSync = data.lastSync;
            this.updateSyncStatus('synced', `已同步 (${new Date().toLocaleTimeString()})`);

        } catch (error) {
            console.error('云端同步失败:', error);
            this.updateSyncStatus('error', '同步失败: ' + error.message);
            throw error;
        }
    }

    async saveToGist(data) {
        const { gistId, token, filename } = this.GITHUB_CONFIG;

        if (!gistId || gistId === '1234567890abcdef') {
            throw new Error('请先配置有效的 Gist ID');
        }

        if (!token) {
            throw new Error('保存数据需要 GitHub Token，请配置后重试');
        }

        const response = await fetch(`https://api.github.com/gists/${gistId}`, {
            method: 'PATCH',
            headers: {
                'Authorization': `token ${token}`,
                'Content-Type': 'application/json',
                'Accept': 'application/vnd.github.v3+json'
            },
            body: JSON.stringify({
                files: {
                    [filename]: {
                        content: JSON.stringify(data, null, 2)
                    }
                }
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`Gist 保存失败: ${errorData.message || response.status}`);
        }

        return await response.json();
    }

    async simulateCloudSave(data) {
        // 移除模拟方法，使用真实的 Gist 保存
        return this.saveToGist(data);
    }

    async syncWithCloud() {
        try {
            await this.saveToCloud();
        } catch (error) {
            alert('同步失败，请检查网络连接后重试');
        }
    }

    setupAutoSync() {
        // 每5分钟自动同步一次
        setInterval(() => {
            this.saveToCloud().catch(error => {
                console.warn('自动同步失败:', error);
            });
        }, 5 * 60 * 1000);

        // 页面卸载前同步
        window.addEventListener('beforeunload', () => {
            this.saveToCloud().catch(error => {
                console.warn('页面卸载时同步失败:', error);
            });
        });
    }

    updateSyncStatus(status, message) {
        const statusElement = document.getElementById('sync-status');
        if (statusElement) {
            statusElement.textContent = message;
            statusElement.className = `sync-status ${status}`;
        }
    }

    updateCycleInfo() {
        const cycleElement = document.getElementById('current-cycle');
        if (cycleElement) {
            cycleElement.textContent = this.currentCycle;
        }

        const today = new Date();
        const weekStart = this.getWeekStart(today);
        const weekEnd = new Date(weekStart);
        weekEnd.setDate(weekStart.getDate() + 6);

        const formatDate = (date) => `${date.getMonth() + 1}/${date.getDate()}`;
        const weekDateElement = document.getElementById('current-week-date');
        if (weekDateElement) {
            weekDateElement.textContent = `${formatDate(weekStart)} - ${formatDate(weekEnd)}`;
        }

        const lastSyncElement = document.getElementById('last-sync');
        if (lastSyncElement) {
            if (this.lastSync) {
                const syncDate = new Date(this.lastSync);
                lastSyncElement.textContent = syncDate.toLocaleString('zh-CN');
            } else {
                lastSyncElement.textContent = '从未';
            }
        }
    }

    getWeekStart(date) {
        const d = new Date(date);
        const day = d.getDay();
        const diff = d.getDate() - day + (day === 0 ? -6 : 1);
        return new Date(d.setDate(diff));
    }

    initializeSchedule() {
        if (this.currentWeekPresenters.length === 0) {
            this.autoFillCurrentWeek();
        }

        if (this.nextWeekPresenters.length === 0) {
            this.autoFillNextWeek();
        }
    }

    autoFillCurrentWeek() {
        const pendingMembers = this.getPendingMembers();
        const selectedMembers = pendingMembers.slice(0, 2).map(m => m.id);
        this.currentWeekPresenters = selectedMembers;
    }

    autoFillNextWeek() {
        const pendingMembers = this.getPendingMembers().filter(m =>
            !this.currentWeekPresenters.includes(m.id)
        );
        const selectedMembers = pendingMembers.slice(0, 2).map(m => m.id);
        this.nextWeekPresenters = selectedMembers;
    }

    getPendingMembers() {
        return this.members.filter(m =>
            m.cycleCount !== this.currentCycle &&
            !this.currentWeekPresenters.includes(m.id) &&
            !this.nextWeekPresenters.includes(m.id)
        ).sort((a, b) => {
            if (!a.lastPresented && !b.lastPresented) return 0;
            if (!a.lastPresented) return -1;
            if (!b.lastPresented) return 1;
            return new Date(a.lastPresented) - new Date(b.lastPresented);
        });
    }

    getMemberStatus(member) {
        if (this.currentWeekPresenters.includes(member.id)) {
            return 'current';
        } else if (this.nextWeekPresenters.includes(member.id)) {
            return 'next';
        } else if (member.cycleCount === this.currentCycle) {
            return 'presented';
        } else {
            return 'pending';
        }
    }

    getMemberZone(member) {
        const status = this.getMemberStatus(member);
        if (status === 'current') return 'current-presenters';
        if (status === 'next') return 'next-presenters';
        if (status === 'presented') return 'presented-members';
        return 'pending-members';
    }

    renderMembers() {
        // 清空所有区域
        document.getElementById('current-presenters').innerHTML = '';
        document.getElementById('next-presenters').innerHTML = '';
        document.getElementById('presented-members').innerHTML = '';
        document.getElementById('pending-members').innerHTML = '';

        // 渲染每个成员到对应区域
        this.members.forEach(member => {
            const card = this.createMemberCard(member);
            const zoneId = this.getMemberZone(member);
            document.getElementById(zoneId).appendChild(card);
        });

        // 更新提示文本
        this.updateZoneHints();
    }

    createMemberCard(member) {
        const card = document.createElement('div');
        card.className = 'member-card';
        card.draggable = true;
        card.dataset.memberId = member.id;

        const status = this.getMemberStatus(member);
        const statusText = {
            'current': '本周',
            'next': '下周',
            'presented': '已报',
            'pending': '待报'
        };

        const lastDate = member.lastPresented ?
            new Date(member.lastPresented).toLocaleDateString('zh-CN', {month: 'short', day: 'numeric'}) :
            '';

        card.innerHTML = `
            <span class="name">${member.name}</span>
            <span class="status ${status}">${statusText[status]}</span>
            ${lastDate ? `<span class="last-date">${lastDate}</span>` : ''}
        `;

        return card;
    }

    updateZoneHints() {
        const zones = [
            { id: 'current-presenters', hint: '本周汇报人员' },
            { id: 'next-presenters', hint: '下周准备汇报人员' },
            { id: 'presented-members', hint: '本周期已汇报的成员' },
            { id: 'pending-members', hint: '待汇报的成员' }
        ];

        zones.forEach(zone => {
            const element = document.getElementById(zone.id);
            const hasMembers = element.querySelector('.member-card');

            if (!hasMembers) {
                if (!element.querySelector('.zone-hint')) {
                    const hint = document.createElement('div');
                    hint.className = 'zone-hint';
                    hint.textContent = zone.hint;
                    element.appendChild(hint);
                }
                element.classList.add('empty-zone');
                element.classList.remove('non-empty-zone');
            } else {
                const hint = element.querySelector('.zone-hint');
                if (hint) hint.remove();
                element.classList.add('non-empty-zone');
                element.classList.remove('empty-zone');
            }
        });
    }

    setupDragAndDrop() {
        const container = document.getElementById('weekly-schedule-container');

        // 设置拖拽事件
        container.addEventListener('dragstart', (e) => {
            if (e.target.classList.contains('member-card')) {
                e.target.classList.add('dragging');
                e.dataTransfer.setData('text/plain', e.target.dataset.memberId);
                e.dataTransfer.effectAllowed = 'move';
            }
        });

        container.addEventListener('dragend', (e) => {
            if (e.target.classList.contains('member-card')) {
                e.target.classList.remove('dragging');
            }
        });

        // 设置放置区域事件
        const dropZones = ['current-presenters', 'next-presenters', 'presented-members', 'pending-members'];

        dropZones.forEach(zoneId => {
            const zone = document.getElementById(zoneId);

            zone.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                zone.classList.add('drag-over');
            });

            zone.addEventListener('dragleave', (e) => {
                if (!zone.contains(e.relatedTarget)) {
                    zone.classList.remove('drag-over');
                }
            });

            zone.addEventListener('drop', (e) => {
                e.preventDefault();
                zone.classList.remove('drag-over');

                const memberId = parseInt(e.dataTransfer.getData('text/plain'));
                const member = this.members.find(m => m.id === memberId);

                if (member) {
                    this.moveMemberToZone(member, zoneId);
                }
            });
        });
    }

    async moveMemberToZone(member, targetZoneId) {
        const today = new Date();

        // 先从所有列表中移除该成员
        this.currentWeekPresenters = this.currentWeekPresenters.filter(id => id !== member.id);
        this.nextWeekPresenters = this.nextWeekPresenters.filter(id => id !== member.id);

        // 根据目标区域更新成员状态
        if (targetZoneId === 'current-presenters') {
            this.currentWeekPresenters.push(member.id);
        } else if (targetZoneId === 'next-presenters') {
            this.nextWeekPresenters.push(member.id);
        } else if (targetZoneId === 'presented-members') {
            member.lastPresented = today.toISOString();
            member.cycleCount = this.currentCycle;
        }

        this.renderMembers();

        // 自动保存到云端
        try {
            await this.saveToCloud();
        } catch (error) {
            console.warn('自动同步失败:', error);
        }

        // 添加动画效果
        setTimeout(() => {
            const card = document.querySelector(`[data-member-id="${member.id}"]`);
            if (card) {
                card.classList.add('dropped');
                setTimeout(() => card.classList.remove('dropped'), 300);
            }
        }, 50);
    }

    async resetAll() {
        if (!confirm('确定要重置所有数据吗？此操作不可恢复！')) {
            return;
        }

        this.loadDefaultData();
        this.initializeSchedule();

        try {
            await this.saveToCloud();
        } catch (error) {
            console.warn('重置后同步失败:', error);
        }

        this.updateCycleInfo();
        this.renderMembers();

        alert('所有数据已重置！');
    }

    loadConfig() {
        const savedConfig = localStorage.getItem('sage_gist_config');
        if (savedConfig) {
            try {
                const config = JSON.parse(savedConfig);
                this.GITHUB_CONFIG = { ...this.GITHUB_CONFIG, ...config };
            } catch (error) {
                console.warn('配置加载失败:', error);
            }
        }
    }

    saveConfig() {
        localStorage.setItem('sage_gist_config', JSON.stringify({
            gistId: this.GITHUB_CONFIG.gistId,
            token: this.GITHUB_CONFIG.token
        }));
    }

    showConfig() {
        const currentGistId = this.GITHUB_CONFIG.gistId;
        const hasToken = this.GITHUB_CONFIG.token ? '已配置' : '未配置';

        const newGistId = prompt('请输入 Gist ID:', currentGistId);
        if (newGistId !== null && newGistId !== currentGistId) {
            this.GITHUB_CONFIG.gistId = newGistId.trim();
        }

        const tokenAction = confirm(`GitHub Token 状态: ${hasToken}\n\n点击"确定"重新配置 Token，点击"取消"保持当前配置`);
        if (tokenAction) {
            const newToken = prompt('请输入 GitHub Token (用于写入权限):');
            if (newToken !== null) {
                this.GITHUB_CONFIG.token = newToken.trim();
            }
        }

        this.saveConfig();

        // 测试配置
        this.testConnection();
    }

    // 安全的 Token 配置方法
    showTokenConfig() {
        document.getElementById('token-config-modal').style.display = 'block';

        // 清空输入框
        document.getElementById('gist-token').value = '';

        // 显示当前 Token 状态
        const hasToken = this.GITHUB_CONFIG.token ? '✅ 已配置' : '❌ 未配置';
        console.log('🔑 Token 状态:', hasToken);
    }

    hideTokenConfig() {
        document.getElementById('token-config-modal').style.display = 'none';

        // 清空输入框（安全措施）
        document.getElementById('gist-token').value = '';
    }

    setGistToken() {
        const tokenInput = document.getElementById('gist-token');
        const token = tokenInput.value.trim();

        if (!token) {
            alert('请输入有效的 GitHub Token');
            return;
        }

        // 验证 Token 格式
        if (!token.startsWith('ghp_') && !token.startsWith('github_pat_')) {
            if (!confirm('Token 格式可能不正确，是否继续？\n\n有效格式：ghp_xxxx 或 github_pat_xxxx')) {
                return;
            }
        }

        // 设置 Token（仅在当前会话中）
        this.GITHUB_CONFIG.token = token;
        window.SAGE_RUNTIME_CONFIG.gistToken = token;

        // 清空输入框（安全措施）
        tokenInput.value = '';

        // 隐藏弹窗
        this.hideTokenConfig();

        // 显示成功消息
        this.updateSyncStatus('synced', '🔑 Token 已设置（当前会话有效）');

        console.log('🔑 GitHub Token 已设置，可以使用云端同步功能');

        // 可选：自动测试连接
        setTimeout(() => {
            this.testConnection();
        }, 1000);
    }

    async testConnection() {
        this.updateSyncStatus('syncing', '测试连接...');

        try {
            await this.fetchFromGist();
            this.updateSyncStatus('synced', '连接成功！');

            // 重新加载数据
            await this.loadFromCloud();
            this.renderMembers();

        } catch (error) {
            this.updateSyncStatus('error', '连接失败: ' + error.message);
        }
    }
}

// 全局实例
let scheduler;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    scheduler = new CloudSyncScheduler();

    // 点击弹窗外部关闭弹窗
    window.onclick = function(event) {
        const modal = document.getElementById('token-config-modal');
        if (event.target === modal) {
            scheduler.hideTokenConfig();
        }
    }
});
</script>
