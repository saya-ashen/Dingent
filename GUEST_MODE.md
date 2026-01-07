# Guest Mode Documentation (游客模式文档)

## Overview (概述)

Dingent now supports guest-level conversations, allowing users to interact with your AI agents without requiring authentication or creating an account. Workspace owners can control which workspaces allow guest access via the admin UI.

现在 Dingent 支持游客级别的对话功能，允许用户无需身份验证或创建账户即可与您的 AI 代理进行交互。工作空间所有者可以通过管理界面控制哪些工作空间允许游客访问。

## Workspace Access Control (工作空间访问控制)

### Enabling Guest Access (启用游客访问)

Workspace owners can enable guest access through the admin UI:

工作空间所有者可以通过管理界面启用游客访问：

1. Open workspace settings (设置图标)
2. Navigate to "General" tab (导航到"常规"选项卡)
3. Toggle "Guest Access" switch (切换"游客访问"开关)
4. Copy the shareable link (复制可分享链接)
5. Share the link with guests (与游客分享链接)

**Shareable Link Format:** `https://your-domain.com/{workspace-slug}/chat`

**可分享链接格式：** `https://your-domain.com/{workspace-slug}/chat`

### Access Control (访问控制)

- Only workspaces with `allow_guest_access=true` accept guest users
- Guests attempting to access restricted workspaces receive a 403 error
- Workspace owners can disable guest access at any time
- Disabling guest access does not delete existing guest conversations

- 只有 `allow_guest_access=true` 的工作空间才接受游客用户
- 尝试访问受限工作空间的游客会收到 403 错误
- 工作空间所有者可以随时禁用游客访问
- 禁用游客访问不会删除现有的游客对话

## How It Works (工作原理)

### Visitor Identification (访客识别)

Guest users are identified by a `visitor_id`, which is a unique identifier sent via the `X-Visitor-ID` HTTP header. The frontend application should:

游客用户通过 `visitor_id` 进行识别，这是通过 `X-Visitor-ID` HTTP 头发送的唯一标识符。前端应用应该：

1. Generate a UUID on first visit and store it in localStorage/sessionStorage
2. Include this UUID in the `X-Visitor-ID` header for all guest API requests
3. Reuse the same UUID for returning visitors to maintain their conversation history

1. 首次访问时生成 UUID 并存储在 localStorage/sessionStorage 中
2. 在所有游客 API 请求的 `X-Visitor-ID` 头中包含此 UUID
3. 重复使用相同的 UUID 让回访者能够保持其对话历史

### Data Isolation (数据隔离)

- Guest conversations are stored with `user_id=NULL` and their unique `visitor_id`
- Guests can only access their own conversations (matched by `visitor_id`)
- Workspace isolation is maintained - guests still need a valid workspace slug
- Authenticated users cannot access guest conversations and vice versa

- 游客对话存储时 `user_id=NULL`，仅包含其唯一的 `visitor_id`
- 游客只能访问自己的对话（通过 `visitor_id` 匹配）
- 工作空间隔离仍然保持 - 游客仍需要有效的工作空间 slug
- 已认证用户无法访问游客对话，反之亦然

## API Endpoints (API 端点)

### Guest Endpoints (游客端点)

All guest endpoints are prefixed with `/guest` and follow the same pattern as authenticated endpoints:

所有游客端点都以 `/guest` 为前缀，遵循与已认证端点相同的模式：

#### 1. Get Available Agents (获取可用代理)

```http
GET /api/v1/{workspace_slug}/chat/guest/info
POST /api/v1/{workspace_slug}/chat/guest/info
```

**Headers:**
- `X-Visitor-ID`: Optional for this endpoint (用于此端点是可选的)

**Response:** List of available agents

#### 2. Run Agent (运行代理)

```http
POST /api/v1/{workspace_slug}/chat/guest/agent/{agent_id}/run
```

**Headers:**
- `X-Visitor-ID`: **Required** (必需)
- `Content-Type`: application/json

**Body:**
```json
{
  "thread_id": "uuid-v4-string",
  "run_id": "uuid-v4-string",
  "messages": [...],
  "state": {},
  "forwarded_props": {}
}
```

**Response:** Server-Sent Events stream of agent execution

#### 3. Connect to Existing Thread (连接到现有对话)

```http
POST /api/v1/{workspace_slug}/chat/guest/agent/{agent_id}/connect
```

**Headers:**
- `X-Visitor-ID`: **Required** (必需)

**Body:**
```json
{
  "thread_id": "uuid-v4-string",
  "run_id": "uuid-v4-string"
}
```

**Response:** Server-Sent Events stream with conversation history

#### 4. List Guest Threads (列出游客对话)

```http
GET /api/v1/{workspace_slug}/chat/guest/threads
```

**Headers:**
- `X-Visitor-ID`: **Required** (必需)

**Response:**
```json
[
  {
    "id": "uuid",
    "title": "Chat title",
    "created_at": "timestamp",
    "updated_at": "timestamp"
  }
]
```

#### 5. Delete Guest Thread (删除游客对话)

```http
DELETE /api/v1/{workspace_slug}/chat/guest/threads/{thread_id}
```

**Headers:**
- `X-Visitor-ID`: **Required** (必需)

**Response:**
```json
{
  "detail": "Thread deleted successfully"
}
```

## Frontend Integration (前端集成)

### Example: Generate and Store Visitor ID (示例：生成并存储访客 ID)

```javascript
// Get or create visitor ID
function getVisitorId() {
  let visitorId = localStorage.getItem('dingent_visitor_id');
  
  if (!visitorId) {
    // Generate new UUID
    visitorId = crypto.randomUUID();
    localStorage.setItem('dingent_visitor_id', visitorId);
  }
  
  return visitorId;
}

// Use in API calls
const visitorId = getVisitorId();

fetch(`/api/v1/my-workspace/chat/guest/agent/default/run`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Visitor-ID': visitorId
  },
  body: JSON.stringify({
    thread_id: crypto.randomUUID(),
    run_id: crypto.randomUUID(),
    messages: [
      {
        role: 'user',
        content: 'Hello!'
      }
    ]
  })
});
```

### Example: CopilotKit Integration (示例：CopilotKit 集成)

```jsx
import { CopilotKit } from "@copilotkit/react-core";

function GuestChat() {
  const visitorId = getVisitorId();
  
  return (
    <CopilotKit
      runtimeUrl={`/api/v1/my-workspace/chat/guest`}
      headers={{
        'X-Visitor-ID': visitorId
      }}
    >
      {/* Your chat UI */}
    </CopilotKit>
  );
}
```

## Migration Path (迁移路径)

### Converting Guest to Authenticated User (将游客转换为已认证用户)

When a guest user signs up or logs in, you may want to transfer their conversations:

当游客用户注册或登录时，您可能希望转移他们的对话：

```sql
-- Example migration query
UPDATE conversation 
SET user_id = :new_user_id, visitor_id = NULL 
WHERE visitor_id = :old_visitor_id;
```

## Security Considerations (安全考虑)

### Implemented (已实现)

1. **Data Isolation**: Guests can only access their own conversations
   数据隔离：游客只能访问自己的对话

2. **Workspace Isolation**: Guest conversations are still workspace-scoped
   工作空间隔离：游客对话仍然限定在工作空间范围内

3. **No Cross-Access**: Authenticated users cannot access guest conversations
   无交叉访问：已认证用户无法访问游客对话

### Recommended (建议添加)

1. **Rate Limiting**: Implement rate limiting for guest endpoints to prevent abuse
   速率限制：为游客端点实施速率限制以防止滥用

2. **Conversation Cleanup**: Periodically clean up old guest conversations
   对话清理：定期清理旧的游客对话

3. **Feature Restrictions**: Consider limiting guest access to certain features or agents
   功能限制：考虑限制游客访问某些功能或代理

4. **Workspace Access Control**: By default, guests can access any workspace. In production, consider:
   - Adding a `allow_guest_access` boolean field to the Workspace model
   - Checking this field in `get_current_workspace_allow_guest`
   - Only allowing guest access to workspaces explicitly marked as public
   工作空间访问控制：默认情况下，游客可以访问任何工作空间。在生产环境中，考虑：
   - 在 Workspace 模型中添加 `allow_guest_access` 布尔字段
   - 在 `get_current_workspace_allow_guest` 中检查此字段
   - 仅允许游客访问明确标记为公开的工作空间

Example workspace access control implementation:
```python
# Add to Workspace model
allow_guest_access: bool = Field(default=False, description="允许游客访问此工作空间")

# Update get_current_workspace_allow_guest dependency
def get_current_workspace_allow_guest(...):
    workspace = session.exec(statement).first()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # For guests, verify workspace allows guest access
    if not current_user and not workspace.allow_guest_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="This workspace does not allow guest access"
        )
    
    # ... rest of the logic
```

Example rate limiting (FastAPI):
```python
from fastapi_limiter.depends import RateLimiter

@router.post("/guest/agent/{agent_id}/run", 
             dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def run_guest(...):
    ...
```

Example cleanup job (can be added as a background task):
```python
# Clean up guest conversations older than 30 days
from datetime import timedelta
from sqlmodel import select

def cleanup_old_guest_conversations(session: Session, days: int = 30):
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    statement = select(Conversation).where(
        Conversation.visitor_id.is_not(None),
        Conversation.updated_at < cutoff_date
    )
    old_conversations = session.exec(statement).all()
    
    for conv in old_conversations:
        session.delete(conv)
    
    session.commit()
```

## Testing (测试)

### Manual Testing (手动测试)

1. Start the Dingent server
2. Use curl or Postman to test guest endpoints:

```bash
# Generate a visitor ID
VISITOR_ID=$(uuidgen)

# Get available agents
curl -X POST "http://localhost:8000/api/v1/default/chat/guest/info" \
  -H "X-Visitor-ID: $VISITOR_ID"

# Start a conversation
curl -X POST "http://localhost:8000/api/v1/default/chat/guest/agent/default/run" \
  -H "X-Visitor-ID: $VISITOR_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "'$(uuidgen)'",
    "run_id": "'$(uuidgen)'",
    "messages": [
      {
        "role": "user",
        "content": "Hello, I am a guest!"
      }
    ]
  }'
```

## Troubleshooting (故障排除)

### "Guest users must provide X-Visitor-ID header" (游客用户必须提供 X-Visitor-ID 头)

**Solution**: Ensure the `X-Visitor-ID` header is included in all guest API requests
**解决方案**：确保所有游客 API 请求中都包含 `X-Visitor-ID` 头

### "You do not have permission to access this conversation" (您无权访问此对话)

**Solution**: Verify that the `X-Visitor-ID` matches the one used to create the conversation
**解决方案**：验证 `X-Visitor-ID` 与创建对话时使用的 ID 匹配

### Guest cannot see their conversation history (游客看不到对话历史)

**Solution**: Ensure you're using the same `visitor_id` stored in localStorage
**解决方案**：确保使用存储在 localStorage 中的相同 `visitor_id`

## Future Enhancements (未来增强)

1. **Analytics**: Track guest usage patterns
   分析：跟踪游客使用模式

2. **Conversion Tracking**: Monitor guest-to-user conversion rates
   转化跟踪：监控游客到用户的转化率

3. **Guest Quotas**: Limit number of messages or conversations per guest
   游客配额：限制每个游客的消息或对话数量

4. **IP-based Fallback**: Use IP address as fallback identifier if visitor ID is not provided
   基于 IP 的回退：如果未提供访客 ID，使用 IP 地址作为回退标识符
