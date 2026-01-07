# UI Changes for Guest Access Control (UI 变更说明)

## Settings Dialog - General Tab (设置对话框 - 常规选项卡)

### Location (位置)
- Workspace Settings → General Tab
- 工作空间设置 → 常规选项卡

### UI Components Added (新增 UI 组件)

#### 1. Basic Information Section (基本信息部分)
```
┌─────────────────────────────────────────────────────────┐
│ Basic Information                                        │
│                                                          │
│ Workspace Name                                          │
│ [Input: Workspace name                              ]   │
│                                                          │
│ Description                                             │
│ [Input: Workspace description (optional)           ]   │
│                                                          │
│ [Save Changes]                                          │
└─────────────────────────────────────────────────────────┘
```

#### 2. Guest Access Section (游客访问部分)
```
┌─────────────────────────────────────────────────────────┐
│ 🌐 Guest Access                              [Toggle]   │
│    Allow visitors to access your workspace              │
│    without signing in                                   │
│                                                          │
│  When ENABLED:                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 🔗 Shareable Guest Link                          │  │
│  │                                                    │  │
│  │ [https://app.com/my-workspace/chat    ] [Copy]   │  │
│  │                                                    │  │
│  │ Share this link with anyone you want to grant    │  │
│  │ guest access. Guests can chat with AI agents     │  │
│  │ but cannot access workspace settings.            │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │ ℹ️ Security Note                                  │  │
│  │ Guest conversations are isolated and guests       │  │
│  │ cannot access other users' data.                  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### User Flow (用户流程)

1. **Owner Opens Settings (所有者打开设置)**
   - Click settings icon in workspace
   - Select "General" from left sidebar

2. **Enable Guest Access (启用游客访问)**
   - Toggle "Guest Access" switch to ON
   - Shareable link section appears below
   - Link format: `https://[domain]/[workspace-slug]/chat`

3. **Share Link (分享链接)**
   - Click "Copy" button to copy link to clipboard
   - Share link via email, messaging, etc.
   - Guests click link and can start chatting immediately

4. **Disable Guest Access (禁用游客访问)**
   - Toggle switch to OFF
   - Link section disappears
   - New guests cannot access the workspace
   - Existing guest conversations remain but guests cannot continue

### Visual Elements (视觉元素)

#### Colors & Icons (颜色和图标)
- Globe icon (🌐) for guest access section
- External link icon (🔗) for shareable link
- Copy icon for copy button
- Blue info box for security note
- Toggle switch (on/off state)

#### Spacing & Layout (间距和布局)
- Section spacing: 32px between sections
- Left padding for nested content: 24px
- Border radius for boxes: 8px
- Button sizes: Small (sm) for actions

### States (状态)

#### Guest Access Disabled (游客访问禁用)
```
🌐 Guest Access                              [OFF]
   Allow visitors to access your workspace
   without signing in
```

#### Guest Access Enabled (游客访问启用)
```
🌐 Guest Access                              [ON]
   Allow visitors to access your workspace
   without signing in

   [Shareable link section visible]
   [Security note visible]
```

#### Loading State (加载状态)
- Toggle switch shows loading spinner
- Save button disabled with loading text
- Form inputs disabled during update

### Error Handling (错误处理)

#### Success Messages (成功消息)
- "Guest access enabled" - Toast notification
- "Guest access disabled" - Toast notification
- "Guest link copied to clipboard" - Toast notification
- "Workspace updated successfully" - Toast notification

#### Error Messages (错误消息)
- "Failed to update workspace settings" - Toast notification (red)
- "This workspace does not allow guest access" - API error (403)

### Responsive Design (响应式设计)

- Settings dialog: 90vw width, 85vh height
- Max width for content: 2xl (672px)
- Mobile: Stack elements vertically
- Desktop: Optimal spacing and layout

### Accessibility (无障碍访问)

- Labels for all inputs
- ARIA labels for icons
- Keyboard navigation support
- Screen reader compatible
- Focus indicators on interactive elements

## Technical Implementation (技术实现)

### React Components Used (使用的 React 组件)
- `Dialog` - Settings modal container
- `Switch` - Toggle for guest access
- `Input` - Text inputs for name, description, link
- `Button` - Action buttons
- `Label` - Form labels
- `ScrollArea` - Scrollable content area
- Toast notifications via `sonner`

### State Management (状态管理)
- `useWorkspaceStore` - Current workspace data
- `useWorkspaceApi` - API calls
- Local state for form inputs
- Loading states for async operations

### API Integration (API 集成)
- PATCH `/workspaces/{id}` - Update workspace settings
  ```json
  {
    "allow_guest_access": true
  }
  ```

## User Scenarios (用户场景)

### Scenario 1: Public Demo (公开演示)
Owner wants to share AI assistant with potential customers:
1. Enable guest access
2. Copy link
3. Share in marketing materials
4. Guests try the assistant without signup

### Scenario 2: Limited Time Access (限时访问)
Owner wants temporary guest access:
1. Enable guest access before event
2. Share link with attendees
3. Disable after event ends
4. Guest access immediately revoked

### Scenario 3: Private Workspace (私密工作空间)
Owner keeps workspace private:
1. Guest access remains OFF (default)
2. Only invited members can access
3. Guests receive 403 error
4. Secure, members-only collaboration

## Screenshots Locations (截图位置)

The following screenshots would show:
1. Settings dialog with General tab selected
2. Guest Access toggle in OFF state
3. Guest Access toggle in ON state with link visible
4. Copy button interaction
5. Toast notification for successful copy
6. Mobile view of the settings panel

## Next Steps for Testing (测试后续步骤)

1. Start Dingent development server
2. Open workspace settings
3. Navigate to General tab
4. Toggle guest access on/off
5. Verify link format
6. Test copy functionality
7. Share link and verify guest access
8. Test access control (enable/disable)
