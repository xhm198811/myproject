/**
 * Enhanced Clipboard Copy Handler
 * Provides comprehensive copy functionality with visual feedback, error handling, and cross-browser support
 * 
 * Features:
 * - Accurate clipboard copying with fallback methods
 * - Visual feedback (toasts, button states, animations)
 * - Edge case handling (empty content, permissions, large text)
 * - Cross-browser compatibility (modern API + fallback)
 * - Consistent styling with AMIS UI components
 * 
 * Usage:
 * 1. Include script: <script src="/static/js/clipboard-handler.js"></script>
 * 2. Use global: window.clipboardHandler.copyToClipboard('content')
 * 3. In AMIS: onclick="handleCopyAction(event)"
 */

(function(global) {
    'use strict';

    /**
     * Browser capability detection
     */
    const BrowserCapabilities = {
        supportsClipboardAPI: () => {
            return typeof navigator !== 'undefined' && 
                   navigator.clipboard && 
                   typeof navigator.clipboard.writeText === 'function';
        },
        supportsExecCommand: () => {
            return typeof document !== 'undefined' && 
                   typeof document.execCommand === 'function';
        },
        supportsSelection: () => {
            return typeof window !== 'undefined' && 
                   typeof window.getSelection === 'function';
        },
        isSecureContext: () => {
            return typeof window !== 'undefined' && 
                   window.isSecureContext === true;
        },
        isMobile: () => {
            return typeof navigator !== 'undefined' && 
                   (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent));
        },
        isSafari: () => {
            return typeof navigator !== 'undefined' && 
                   /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
        },
        isFirefox: () => {
            return typeof navigator !== 'undefined' && 
                   navigator.userAgent.toLowerCase().indexOf('firefox') > -1;
        }
    };

    /**
     * Enhanced Clipboard Copy Handler
     */
    class ClipboardCopyHandler {
        constructor(options = {}) {
            this.options = {
                successDuration: 3000,
                errorDuration: 5000,
                warningDuration: 4000,
                showToast: true,
                toastPosition: 'top',
                showButtonFeedback: true,
                enableLogging: true,
                maxContentLength: 1000000,
                ...options
            };
            
            this.toastContainer = null;
            this.activeToasts = new Map();
            this.initToastContainer();
            this.log('ClipboardCopyHandler initialized with options:', this.options);
        }

        /**
         * Initialize toast notification container
         */
        initToastContainer() {
            if (this.options.showToast && !document.getElementById('clipboard-toast-container')) {
                this.toastContainer = document.createElement('div');
                this.toastContainer.id = 'clipboard-toast-container';
                this.toastContainer.innerHTML = `
                    <style>
                        #clipboard-toast-container {
                            position: fixed;
                            ${this.options.toastPosition === 'top' ? 'top: 80px;' : 'bottom: 30px;'}
                            left: 50%;
                            transform: translateX(-50%);
                            z-index: 10000;
                            display: flex;
                            flex-direction: column;
                            align-items: center;
                            gap: 10px;
                            pointer-events: none;
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                        }
                        .clipboard-toast {
                            background: white;
                            color: #333;
                            padding: 14px 20px;
                            border-radius: 8px;
                            font-size: 14px;
                            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
                            display: flex;
                            align-items: center;
                            gap: 10px;
                            pointer-events: auto;
                            max-width: 450px;
                            word-break: break-word;
                            animation: clipboardToastIn 0.35s cubic-bezier(0.4, 0, 0.2, 1);
                            border-left: 4px solid #1890ff;
                        }
                        .clipboard-toast.success {
                            background: linear-gradient(135deg, #f6ffed 0%, #ffffff 100%);
                            border-left-color: #52c41a;
                        }
                        .clipboard-toast.error {
                            background: linear-gradient(135deg, #fff2f0 0%, #ffffff 100%);
                            border-left-color: #ff4d4f;
                        }
                        .clipboard-toast.warning {
                            background: linear-gradient(135deg, #fffbe6 0%, #ffffff 100%);
                            border-left-color: #faad14;
                        }
                        .clipboard-toast.info {
                            background: linear-gradient(135deg, #e6f7ff 0%, #ffffff 100%);
                            border-left-color: #1890ff;
                        }
                        .clipboard-toast-icon {
                            font-size: 18px;
                            flex-shrink: 0;
                        }
                        .clipboard-toast.success .clipboard-toast-icon { color: #52c41a; }
                        .clipboard-toast.error .clipboard-toast-icon { color: #ff4d4f; }
                        .clipboard-toast.warning .clipboard-toast-icon { color: #faad14; }
                        .clipboard-toast.info .clipboard-toast-icon { color: #1890ff; }
                        .clipboard-toast-message {
                            flex: 1;
                            line-height: 1.5;
                        }
                        .clipboard-toast-close {
                            background: none;
                            border: none;
                            color: #999;
                            cursor: pointer;
                            font-size: 16px;
                            padding: 0;
                            width: 20px;
                            height: 20px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            border-radius: 50%;
                            transition: all 0.2s;
                        }
                        .clipboard-toast-close:hover {
                            background: #f0f0f0;
                            color: #666;
                        }
                        @keyframes clipboardToastIn {
                            from {
                                opacity: 0;
                                transform: translateY(${this.options.toastPosition === 'top' ? '-20px' : '20px'});
                            }
                            to {
                                opacity: 1;
                                transform: translateX(-50%);
                            }
                        }
                        @keyframes clipboardToastOut {
                            from {
                                opacity: 1;
                                transform: translateX(-50%);
                            }
                            to {
                                opacity: 0;
                                transform: translateY(${this.options.toastPosition === 'top' ? '-20px' : '20px'});
                            }
                        }
                        .clipboard-button-loading {
                            position: relative;
                            pointer-events: none;
                        }
                        .clipboard-button-loading::after {
                            content: '';
                            position: absolute;
                            top: 50%;
                            left: 50%;
                            width: 16px;
                            height: 16px;
                            margin: -8px 0 0 -8px;
                            border: 2px solid rgba(255, 255, 255, 0.3);
                            border-top-color: white;
                            border-radius: 50%;
                            animation: clipboardSpinner 0.6s linear infinite;
                        }
                        @keyframes clipboardSpinner {
                            to { transform: rotate(360deg); }
                        }
                        .clipboard-button-success {
                            animation: clipboardSuccessPulse 0.6s ease-out;
                        }
                        @keyframes clipboardSuccessPulse {
                            0% { transform: scale(1); }
                            50% { transform: scale(1.05); }
                            100% { transform: scale(1); }
                        }
                    </style>
                `;
                document.body.appendChild(this.toastContainer);
            }
        }

        /**
         * Show toast notification with enhanced features
         */
        showToast(message, type = 'info', duration = null) {
            if (!this.options.showToast || !this.toastContainer) return;

            const toastId = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
            const toast = document.createElement('div');
            toast.id = toastId;
            toast.className = `clipboard-toast ${type}`;

            const icons = {
                success: '✓',
                error: '✕',
                warning: '⚠',
                info: 'ℹ'
            };

            toast.innerHTML = `
                <span class="clipboard-toast-icon">${icons[type] || icons.info}</span>
                <span class="clipboard-toast-message">${this.escapeHtml(message)}</span>
                <button class="clipboard-toast-close" onclick="document.getElementById('${toastId}').remove()">×</button>
            `;

            this.toastContainer.appendChild(toast);
            this.activeToasts.set(toastId, toast);

            const actualDuration = duration || 
                (type === 'error' ? this.options.errorDuration :
                 type === 'warning' ? this.options.warningDuration :
                 this.options.successDuration);

            setTimeout(() => {
                this.removeToast(toastId);
            }, actualDuration);

            this.log(`Toast shown: ${message} (${type})`);
        }

        /**
         * Remove toast with animation
         */
        removeToast(toastId) {
            const toast = this.activeToasts.get(toastId);
            if (toast) {
                toast.style.animation = 'clipboardToastOut 0.3s ease-out forwards';
                setTimeout(() => {
                    toast.remove();
                    this.activeToasts.delete(toastId);
                }, 300);
            }
        }

        /**
         * Escape HTML to prevent XSS
         */
        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        /**
         * Main copy method with comprehensive error handling
         */
        async copyToClipboard(text, options = {}) {
            const { 
                showSuccess = true, 
                showError = true,
                customSuccessMessage = null,
                customErrorMessage = null
            } = options;

            this.log('copyToClipboard called', { textLength: text?.length, options });

            if (!text || text.trim() === '') {
                this.log('Empty content detected');
                this.showToast('复制内容不能为空', 'warning');
                return false;
            }

            if (text.length > this.options.maxContentLength) {
                this.log('Content too large', { length: text.length, max: this.options.maxContentLength });
                this.showToast(`内容过大（${this.formatBytes(text.length)}），无法复制`, 'error');
                return false;
            }

            try {
                const success = await this.attemptCopy(text);
                
                if (success) {
                    if (showSuccess) {
                        this.showToast(customSuccessMessage || '复制成功', 'success');
                    }
                    this.log('Copy successful');
                    return true;
                } else {
                    throw new Error('Copy operation returned false');
                }
            } catch (error) {
                this.log('Copy failed', { error: error.message, stack: error.stack });
                
                if (showError) {
                    const errorMsg = this.getErrorMessage(error);
                    this.showToast(customErrorMessage || errorMsg, 'error');
                }
                return false;
            }
        }

        /**
         * Attempt copy with multiple fallback methods
         */
        async attemptCopy(text) {
            this.log('Attempting copy with available methods');

            if (BrowserCapabilities.supportsClipboardAPI()) {
                this.log('Using modern Clipboard API');
                const result = await this.copyWithClipboardAPI(text);
                if (result) return true;
            }

            if (BrowserCapabilities.supportsExecCommand()) {
                this.log('Using execCommand fallback');
                const result = await this.copyWithExecCommand(text);
                if (result) return true;
            }

            throw new Error('No available copy method');
        }

        /**
         * Copy using modern Clipboard API
         */
        async copyWithClipboardAPI(text) {
            try {
                await navigator.clipboard.writeText(text);
                this.log('Clipboard API success');
                return true;
            } catch (error) {
                this.log('Clipboard API failed', { error: error.message });
                
                if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
                    throw new Error('剪贴板权限被拒绝，请允许浏览器访问剪贴板');
                } else if (error.name === 'NotSupportedError') {
                    throw new Error('当前浏览器不支持剪贴板API');
                } else {
                    throw error;
                }
            }
        }

        /**
         * Copy using execCommand fallback
         */
        async copyWithExecCommand(text) {
            return new Promise((resolve, reject) => {
                try {
                    const textArea = document.createElement('textarea');
                    textArea.value = text;
                    textArea.style.position = 'fixed';
                    textArea.style.left = '-9999px';
                    textArea.style.top = '-9999px';
                    textArea.style.opacity = '0';
                    textArea.setAttribute('readonly', '');
                    textArea.style.fontSize = '12pt';
                    textArea.style.padding = '0';
                    textArea.style.border = 'none';
                    textArea.style.outline = 'none';
                    textArea.style.boxShadow = 'none';
                    textArea.style.background = 'transparent';
                    
                    document.body.appendChild(textArea);

                    if (BrowserCapabilities.supportsSelection()) {
                        const selection = window.getSelection();
                        const range = document.createRange();
                        selection.removeAllRanges();
                        range.selectNodeContents(textArea);
                        selection.addRange(range);
                        textArea.setSelectionRange(0, text.length);
                    } else {
                        textArea.select();
                    }

                    const successful = document.execCommand('copy');
                    document.body.removeChild(textArea);

                    if (successful) {
                        this.log('execCommand success');
                        resolve(true);
                    } else {
                        throw new Error('execCommand returned false');
                    }
                } catch (error) {
                    this.log('execCommand failed', { error: error.message });
                    reject(error);
                }
            });
        }

        /**
         * Get user-friendly error message
         */
        getErrorMessage(error) {
            const message = error.message || error.toString();
            
            if (message.includes('permission') || message.includes('NotAllowed')) {
                return '剪贴板权限被拒绝，请检查浏览器设置';
            } else if (message.includes('not supported') || message.includes('NotSupported')) {
                return '当前浏览器不支持此功能，请尝试其他浏览器';
            } else if (message.includes('secure context') || message.includes('HTTPS')) {
                return '剪贴板功能需要HTTPS环境';
            } else if (message.includes('execCommand')) {
                return '复制失败，请手动选择内容复制';
            } else {
                return `复制失败: ${message}`;
            }
        }

        /**
         * Format bytes to human readable size
         */
        formatBytes(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
        }

        /**
         * Add loading state to button
         */
        setButtonLoading(button) {
            if (!button || !this.options.showButtonFeedback) return;
            
            button.dataset.originalContent = button.innerHTML;
            button.dataset.originalDisabled = button.disabled;
            button.disabled = true;
            button.classList.add('clipboard-button-loading');
            
            const icon = button.querySelector('.fa, .icon');
            if (icon) {
                icon.style.opacity = '0.3';
            }
        }

        /**
         * Reset button state
         */
        resetButton(button, success = true) {
            if (!button || !this.options.showButtonFeedback) return;
            
            button.disabled = button.dataset.originalDisabled === 'true';
            button.classList.remove('clipboard-button-loading');
            
            const icon = button.querySelector('.fa, .icon');
            if (icon) {
                icon.style.opacity = '1';
            }

            if (success) {
                button.classList.add('clipboard-button-success');
                setTimeout(() => {
                    button.classList.remove('clipboard-button-success');
                }, 600);
            }

            if (button.dataset.originalContent) {
                button.innerHTML = button.dataset.originalContent;
            }
        }

        /**
         * Copy table row data
         */
        async copyTableRow(row, columns = []) {
            const data = {};
            columns.forEach(col => {
                const cell = row.querySelector(`[data-field="${col.name}"]`) || 
                             row.querySelector(`td:nth-child(${col.index + 1})`);
                if (cell) {
                    data[col.label || col.name] = cell.textContent.trim();
                }
            });
            return this.copyToClipboard(JSON.stringify(data, null, 2));
        }

        /**
         * Copy URL
         */
        async copyUrl(url) {
            if (!url || url.trim() === '') {
                this.showToast('链接地址不能为空', 'warning');
                return false;
            }
            return this.copyToClipboard(url.trim());
        }

        /**
         * Copy JSON data
         */
        async copyJson(data, formatted = true) {
            try {
                const text = formatted ? JSON.stringify(data, null, 2) : JSON.stringify(data);
                return this.copyToClipboard(text);
            } catch (error) {
                this.showToast('JSON数据格式错误', 'error');
                return false;
            }
        }

        /**
         * Copy Markdown format
         */
        async copyMarkdown(title, data, fields = null) {
            const lines = [`## ${this.escapeHtml(title)}`, ''];
            lines.push('| 字段 | 值 |');
            lines.push('|------|-----|');

            const targetFields = fields || Object.keys(data);
            targetFields.forEach(key => {
                const value = data[key] !== undefined ? String(data[key]) : '';
                const escapedValue = this.escapeHtml(value.replace(/\|/g, '\\|').replace(/\n/g, ' '));
                lines.push(`| ${key} | ${escapedValue} |`);
            });

            lines.push('');
            return this.copyToClipboard(lines.join('\n'));
        }

        /**
         * Copy plain text table
         */
        async copyPlainText(title, data) {
            const lines = [];
            lines.push('═'.repeat(50));
            lines.push(this.escapeHtml(title));
            lines.push('═'.repeat(50));

            Object.entries(data).forEach(([key, value]) => {
                if (value !== undefined && value !== null) {
                    lines.push(`${key}: ${value}`);
                }
            });

            lines.push('═'.repeat(50));
            lines.push('');
            return this.copyToClipboard(lines.join('\n'));
        }

        /**
         * Logging method
         */
        log(...args) {
            if (this.options.enableLogging) {
                console.log('[ClipboardHandler]', ...args);
            }
        }
    }

    /**
     * AMIS copy button event handler - handles copy action directly
     */
    async function handleCopyAction(event) {
        event.preventDefault();
        event.stopPropagation();

        const button = event.currentTarget;
        const handler = window.clipboardHandler;

        if (!handler) {
            console.error('[ClipboardHandler] Clipboard handler not initialized');
            return;
        }

        handler.setButtonLoading(button);

        const copyType = button.dataset.copyType || 'amis';
        const copyApi = button.dataset.copyApi;

        try {
            let success = false;
            let message = '复制成功';

            if (copyType === 'amis' && copyApi) {
                handler.log('[ClipboardHandler] Making copy request to:', copyApi);

                const response = await fetch(copyApi, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    }
                });

                handler.log('[ClipboardHandler] Response status:', response.status);

                if (!response.ok) {
                    const errorText = await response.text();
                    handler.log('[ClipboardHandler] Error response:', errorText);
                    try {
                        const errorData = JSON.parse(errorText);
                        message = errorData.msg || `请求失败 (${response.status})`;
                    } catch {
                        message = `请求失败 (${response.status})`;
                    }
                    handler.showToast(message, 'error');
                    handler.resetButton(button, false);
                    return;
                }

                const result = await response.json();
                handler.log('[ClipboardHandler] Copy response:', result);

                if (result.data && result.data.copy_success && result.data.copy_content) {
                    success = await handler.copyToClipboard(result.data.copy_content, {
                        showSuccess: false
                    });
                    message = result.msg || '复制成功';
                } else {
                    message = result.msg || '复制失败';
                }

                handler.showToast(message, success ? 'success' : 'error');
            } else if (copyType === 'text') {
                const content = button.dataset.copyContent || '';
                success = await handler.copyToClipboard(content);
            }

            handler.resetButton(button, success);
        } catch (error) {
            console.error('[ClipboardHandler] Copy action failed:', error);
            handler.showToast('复制操作失败，请重试: ' + error.message, 'error');
            handler.resetButton(button, false);
        }
    }

    /**
     * Intercept AMIS Ajax responses for copy operations
     * Hooks into AMIS's built-in action handling
     */
    /**
     * Initialize AMIS response interception for clipboard operations
     */
    function interceptAmisCopyResponse() {
        const handler = window.clipboardHandler;
        if (!handler) return;

        handler.log('[ClipboardHandler] Initializing AMIS response interception');

        const originalFetch = window.fetch;
        window.fetch = async function(...args) {
            const response = await originalFetch.apply(this, args);

            const clone = response.clone();
            try {
                const data = await clone.json();

                if (data && data.data && data.data.copy_success && data.data.copy_content) {
                    await handler.copyToClipboard(data.data.copy_content, {
                        showSuccess: false
                    });
                    handler.showToast(data.msg || '复制成功', 'success');
                    handler.log('[ClipboardHandler] Copy successful via fetch interception');
                }
            } catch (e) {
                console.warn('[ClipboardHandler] Failed to parse fetch response:', e);
            }

            return response;
        };

        const originalXHROpen = XMLHttpRequest.prototype.open;
        const originalXHRSend = XMLHttpRequest.prototype.send;

        XMLHttpRequest.prototype.open = function(method, url) {
            this._url = url;
            return originalXHROpen.apply(this, arguments);
        };

        XMLHttpRequest.prototype.send = function() {
            this.addEventListener('load', function() {
                if (this._url && this._url.includes('clipboard')) {
                    try {
                        const data = JSON.parse(this.responseText);
                        if (data && data.data && data.data.copy_success && data.data.copy_content) {
                            const handler = window.clipboardHandler;
                            if (handler) {
                                handler.copyToClipboard(data.data.copy_content, {
                                    showSuccess: false
                                });
                                handler.showToast(data.msg || '复制成功', 'success');
                                handler.log('[ClipboardHandler] Copy successful via XHR interception');
                            }
                        }
                    } catch (e) {
                        console.warn('[ClipboardHandler] Failed to parse XHR response:', e);
                    }
                }
            });
            return originalXHRSend.apply(this, arguments);
        };

        handler.log('[ClipboardHandler] AMIS response interception initialized');
    }

    /**
     * Initialize all copy buttons on page
     */
    function initCopyButtons() {
        const buttons = document.querySelectorAll('[data-action="copy"], .copy-button, [data-copy-action]');
        buttons.forEach(button => {
            if (!button.dataset.initialized) {
                button.addEventListener('click', handleCopyAction);
                button.dataset.initialized = 'true';
            }
        });
    }

    /**
     * Add copy buttons to table rows
     */
    function addCopyButtonsToTable(tableSelector, options = {}) {
        const defaults = {
            columnIndex: -1,
            copyFields: [],
            buttonIcon: 'fa fa-copy',
            buttonLabel: '复制',
            buttonClass: 'btn-light',
            position: 'before'
        };
        const config = { ...defaults, ...options };

        const table = document.querySelector(tableSelector);
        if (!table) return;

        const rows = table.querySelectorAll('tbody tr, .amis-table-row');
        rows.forEach((row, rowIndex) => {
            const cell = config.columnIndex >= 0 
                ? row.children[config.columnIndex] 
                : row.lastElementChild;

            if (cell && !cell.querySelector('[data-action="copy"]')) {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = `btn btn-xs ${config.buttonClass}`;
                button.dataset.action = 'copy';
                button.dataset.copyType = 'table';
                button.dataset.rowIndex = rowIndex;
                button.innerHTML = `<i class="${config.buttonIcon}"></i> ${config.buttonLabel}`;
                button.title = '复制此行数据';

                if (config.position === 'before') {
                    cell.insertBefore(button, cell.firstChild);
                } else {
                    cell.appendChild(button);
                }

                button.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const handler = window.clipboardHandler;
                    handler.setButtonLoading(button);

                    const rowData = {};
                    config.copyFields.forEach(field => {
                        const fieldCell = row.querySelector(`[data-field="${field}"]`) ||
                                        row.children[config.copyFields.indexOf(field)];
                        if (fieldCell) {
                            rowData[field] = fieldCell.textContent.trim();
                        }
                    });

                    await handler.copyPlainText(
                        options.title || `记录 ${rowIndex + 1}`,
                        rowData
                    );
                    handler.resetButton(button);
                });
            }
        });
    }

    /**
     * Copy current page URL
     */
    async function copyCurrentUrl() {
        const handler = window.clipboardHandler;
        const url = window.location.href;
        return handler.copyToClipboard(url);
    }

    /**
     * Copy element text content
     */
    async function copyElementText(elementId) {
        const element = document.getElementById(elementId);
        if (!element) {
            window.clipboardHandler.showToast(`元素 ${elementId} 不存在`, 'error');
            return false;
        }
        return window.clipboardHandler.copyToClipboard(element.textContent.trim());
    }

    /**
     * Check clipboard permissions
     */
    async function checkClipboardPermission() {
        if (BrowserCapabilities.supportsClipboardAPI() && navigator.permissions) {
            try {
                const result = await navigator.permissions.query({ name: 'clipboard-write' });
                return result.state;
            } catch (e) {
                console.warn('Cannot check clipboard permission:', e);
            }
        }
        return 'unknown';
    }

    /**
     * Request clipboard permission
     */
    async function requestClipboardPermission() {
        if (BrowserCapabilities.supportsClipboardAPI()) {
            try {
                await navigator.clipboard.writeText('');
                return true;
            } catch (e) {
                console.warn('Clipboard permission denied:', e);
                return false;
            }
        }
        return false;
    }

    // Initialize global instance
    global.clipboardHandler = new ClipboardCopyHandler();
    global.handleCopyAction = handleCopyAction;
    global.initCopyButtons = initCopyButtons;
    global.addCopyButtonsToTable = addCopyButtonsToTable;
    global.copyCurrentUrl = copyCurrentUrl;
    global.copyElementText = copyElementText;
    global.checkClipboardPermission = checkClipboardPermission;
    global.requestClipboardPermission = requestClipboardPermission;
    global.BrowserCapabilities = BrowserCapabilities;

    // Initialize AMIS response interception
    interceptAmisCopyResponse();

    // Watch for DOM changes
    if (typeof MutationObserver !== 'undefined') {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach(mutation => {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === 1) {
                        if (node.matches('[data-action="copy"], .copy-button')) {
                            node.addEventListener('click', handleCopyAction);
                            node.dataset.initialized = 'true';
                        }
                        const nestedButtons = node.querySelectorAll('[data-action="copy"], .copy-button');
                        nestedButtons.forEach(btn => {
                            if (!btn.dataset.initialized) {
                                btn.addEventListener('click', handleCopyAction);
                                btn.dataset.initialized = 'true';
                            }
                        });
                    }
                });
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    // Initialize on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCopyButtons);
    } else {
        initCopyButtons();
    }

    console.log('%c✓ Enhanced Clipboard Copy Handler initialized', 'color: #52c41a; font-weight: bold; font-size: 14px;');
    console.log('Browser capabilities:', {
        clipboardAPI: BrowserCapabilities.supportsClipboardAPI(),
        execCommand: BrowserCapabilities.supportsExecCommand(),
        secureContext: BrowserCapabilities.isSecureContext(),
        mobile: BrowserCapabilities.isMobile()
    });

})(typeof window !== 'undefined' ? window : this);
