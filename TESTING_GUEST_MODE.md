# Testing Guide for Guest Mode (游客模式测试指南)

## Manual Testing (手动测试)

### Prerequisites (前提条件)

1. Start the Dingent server:
   ```bash
   cd your-dingent-project
   uvx dingent dev
   ```

2. Ensure you have a workspace set up (e.g., `default`)

### Test Scenarios (测试场景)

#### Test 1: Guest Can Create Conversation (游客可以创建对话)

**Purpose**: Verify that a guest user can start a new conversation without authentication.
**目的**: 验证游客用户可以在没有身份验证的情况下开始新对话。

```bash
# Generate a visitor ID
VISITOR_ID=$(uuidgen)
THREAD_ID=$(uuidgen)
RUN_ID=$(uuidgen)

# Test the guest run endpoint
curl -X POST "http://localhost:8000/api/v1/default/chat/guest/agent/default/run" \
  -H "X-Visitor-ID: $VISITOR_ID" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d "{
    \"thread_id\": \"$THREAD_ID\",
    \"run_id\": \"$RUN_ID\",
    \"messages\": [
      {
        \"id\": \"$(uuidgen)\",
        \"role\": \"user\",
        \"content\": \"Hello, I am testing guest mode!\"
      }
    ],
    \"state\": {},
    \"forwarded_props\": {}
  }"
```

**Expected Result**:
- Server responds with streaming events
- No authentication error
- Conversation is created in database with `visitor_id` set

#### Test 2: Guest Can List Their Conversations (游客可以列出自己的对话)

**Purpose**: Verify guest can retrieve their conversation history.
**目的**: 验证游客可以检索其对话历史。

```bash
# Use the same VISITOR_ID from Test 1
curl -X GET "http://localhost:8000/api/v1/default/chat/guest/threads" \
  -H "X-Visitor-ID: $VISITOR_ID"
```

**Expected Result**:
- Returns JSON array of conversations
- Only includes conversations created with this `visitor_id`
- At least one conversation from Test 1

#### Test 3: Guest Cannot Access Other Guest's Conversations (游客无法访问其他游客的对话)

**Purpose**: Verify data isolation between guests.
**目的**: 验证游客之间的数据隔离。

```bash
# Create conversation with first visitor
VISITOR_ID_1=$(uuidgen)
THREAD_ID_1=$(uuidgen)

curl -X POST "http://localhost:8000/api/v1/default/chat/guest/agent/default/run" \
  -H "X-Visitor-ID: $VISITOR_ID_1" \
  -H "Content-Type: application/json" \
  -d "{
    \"thread_id\": \"$THREAD_ID_1\",
    \"run_id\": \"$(uuidgen)\",
    \"messages\": [{\"id\": \"$(uuidgen)\", \"role\": \"user\", \"content\": \"First visitor\"}]
  }" > /dev/null

# Try to access with different visitor ID
VISITOR_ID_2=$(uuidgen)

curl -X POST "http://localhost:8000/api/v1/default/chat/guest/agent/default/connect" \
  -H "X-Visitor-ID: $VISITOR_ID_2" \
  -H "Content-Type: application/json" \
  -d "{
    \"thread_id\": \"$THREAD_ID_1\",
    \"run_id\": \"$(uuidgen)\"
  }"
```

**Expected Result**:
- Returns 403 Forbidden error
- Message: "You do not have permission to access this conversation."

#### Test 4: Missing X-Visitor-ID Header Returns Error (缺少 X-Visitor-ID 头返回错误)

**Purpose**: Verify that guest endpoints require visitor identification.
**目的**: 验证游客端点需要访客标识。

```bash
curl -X POST "http://localhost:8000/api/v1/default/chat/guest/agent/default/run" \
  -H "Content-Type: application/json" \
  -d "{
    \"thread_id\": \"$(uuidgen)\",
    \"run_id\": \"$(uuidgen)\",
    \"messages\": [{\"id\": \"$(uuidgen)\", \"role\": \"user\", \"content\": \"Test\"}]
  }"
```

**Expected Result**:
- Returns 400 Bad Request
- Message: "Guest users must provide X-Visitor-ID header"

#### Test 5: Guest Can Delete Their Own Conversation (游客可以删除自己的对话)

**Purpose**: Verify guest can manage their conversations.
**目的**: 验证游客可以管理自己的对话。

```bash
# Create a conversation
VISITOR_ID=$(uuidgen)
THREAD_ID=$(uuidgen)

curl -X POST "http://localhost:8000/api/v1/default/chat/guest/agent/default/run" \
  -H "X-Visitor-ID: $VISITOR_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"thread_id\": \"$THREAD_ID\",
    \"run_id\": \"$(uuidgen)\",
    \"messages\": [{\"id\": \"$(uuidgen)\", \"role\": \"user\", \"content\": \"Test\"}]
  }" > /dev/null

# Delete it
curl -X DELETE "http://localhost:8000/api/v1/default/chat/guest/threads/$THREAD_ID" \
  -H "X-Visitor-ID: $VISITOR_ID"

# Try to list - should be empty
curl -X GET "http://localhost:8000/api/v1/default/chat/guest/threads" \
  -H "X-Visitor-ID: $VISITOR_ID"
```

**Expected Result**:
- First DELETE returns: `{"detail": "Thread deleted successfully"}`
- Second GET returns empty array: `[]`

#### Test 6: Workspace Isolation (工作空间隔离)

**Purpose**: Verify conversations are isolated by workspace.
**目的**: 验证对话按工作空间隔离。

```bash
VISITOR_ID=$(uuidgen)

# Create in workspace1
curl -X POST "http://localhost:8000/api/v1/workspace1/chat/guest/agent/default/run" \
  -H "X-Visitor-ID: $VISITOR_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"thread_id\": \"$(uuidgen)\",
    \"run_id\": \"$(uuidgen)\",
    \"messages\": [{\"id\": \"$(uuidgen)\", \"role\": \"user\", \"content\": \"Test workspace1\"}]
  }" > /dev/null

# List in workspace2 - should not see workspace1's conversations
curl -X GET "http://localhost:8000/api/v1/workspace2/chat/guest/threads" \
  -H "X-Visitor-ID: $VISITOR_ID"
```

**Expected Result**:
- Conversations in workspace1 are not visible in workspace2

#### Test 7: Authenticated Users Cannot Access Guest Conversations (已认证用户无法访问游客对话)

**Purpose**: Verify separation between authenticated and guest data.
**目的**: 验证已认证和游客数据之间的分离。

```bash
# Create guest conversation
VISITOR_ID=$(uuidgen)
THREAD_ID=$(uuidgen)

curl -X POST "http://localhost:8000/api/v1/default/chat/guest/agent/default/run" \
  -H "X-Visitor-ID: $VISITOR_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"thread_id\": \"$THREAD_ID\",
    \"run_id\": \"$(uuidgen)\",
    \"messages\": [{\"id\": \"$(uuidgen)\", \"role\": \"user\", \"content\": \"Guest message\"}]
  }" > /dev/null

# Try to access with authenticated user
# First, get a token by logging in
TOKEN=$(curl -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=password" \
  | jq -r '.access_token')

# Try to connect to guest thread
curl -X POST "http://localhost:8000/api/v1/default/chat/agent/default/connect" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"thread_id\": \"$THREAD_ID\",
    \"run_id\": \"$(uuidgen)\"
  }"
```

**Expected Result**:
- Returns 403 Forbidden (authenticated user cannot access guest conversation)

### Frontend Testing (前端测试)

1. Open `examples/guest-chat-example.html` in a web browser
2. Ensure Dingent server is running
3. Open browser console to see the auto-generated Visitor ID
4. Type a message and send
5. Verify:
   - Message appears in UI
   - Network tab shows request with X-Visitor-ID header
   - Response streams back from server
   - Conversation persists on page reload (same visitor ID)

### Database Verification (数据库验证)

After running tests, you can verify the data in the database:

```bash
# Connect to your database
sqlite3 path/to/your/database.db

# Check guest conversations
SELECT id, user_id, visitor_id, workspace_id, title, created_at
FROM conversation
WHERE visitor_id IS NOT NULL;

# Verify user_id is NULL for guest conversations
SELECT COUNT(*) FROM conversation
WHERE visitor_id IS NOT NULL AND user_id IS NOT NULL;
-- Should return 0

# Check workspace isolation
SELECT workspace_id, COUNT(*)
FROM conversation
WHERE visitor_id IS NOT NULL
GROUP BY workspace_id;
```

## Automated Testing (自动化测试)

### pytest Integration Test Example

```python
import pytest
import uuid
from fastapi.testclient import TestClient

def test_guest_conversation_creation(client: TestClient):
    """Test guest can create a conversation."""
    visitor_id = str(uuid.uuid4())
    thread_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())

    response = client.post(
        "/api/v1/default/chat/guest/agent/default/run",
        headers={
            "X-Visitor-ID": visitor_id,
            "Content-Type": "application/json"
        },
        json={
            "thread_id": thread_id,
            "run_id": run_id,
            "messages": [
                {
                    "id": str(uuid.uuid4()),
                    "role": "user",
                    "content": "Hello from pytest!"
                }
            ]
        }
    )

    assert response.status_code == 200

def test_guest_missing_visitor_id(client: TestClient):
    """Test that missing X-Visitor-ID returns error."""
    response = client.post(
        "/api/v1/default/chat/guest/agent/default/run",
        headers={"Content-Type": "application/json"},
        json={
            "thread_id": str(uuid.uuid4()),
            "run_id": str(uuid.uuid4()),
            "messages": [{"id": str(uuid.uuid4()), "role": "user", "content": "Test"}]
        }
    )

    assert response.status_code == 400
    assert "X-Visitor-ID" in response.json()["detail"]

def test_guest_data_isolation(client: TestClient):
    """Test guests cannot access each other's conversations."""
    visitor_1 = str(uuid.uuid4())
    visitor_2 = str(uuid.uuid4())
    thread_id = str(uuid.uuid4())

    # Create conversation as visitor 1
    client.post(
        "/api/v1/default/chat/guest/agent/default/run",
        headers={"X-Visitor-ID": visitor_1},
        json={
            "thread_id": thread_id,
            "run_id": str(uuid.uuid4()),
            "messages": [{"id": str(uuid.uuid4()), "role": "user", "content": "Test"}]
        }
    )

    # Try to access as visitor 2
    response = client.post(
        "/api/v1/default/chat/guest/agent/default/connect",
        headers={"X-Visitor-ID": visitor_2},
        json={
            "thread_id": thread_id,
            "run_id": str(uuid.uuid4())
        }
    )

    assert response.status_code == 403
```

## Performance Testing (性能测试)

### Load Test with Apache Bench

```bash
# Test guest endpoint performance
ab -n 100 -c 10 \
  -H "X-Visitor-ID: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -p guest_request.json \
  http://localhost:8000/api/v1/default/chat/guest/info
```

### Stress Test with wrk

```bash
# Install wrk first
# Test sustained load
wrk -t4 -c100 -d30s \
  -H "X-Visitor-ID: test-visitor-123" \
  http://localhost:8000/api/v1/default/chat/guest/threads
```

## Test Checklist (测试清单)

- [ ] Guest can create conversations without authentication
- [ ] Guest conversations are stored with correct visitor_id
- [ ] Guests can only access their own conversations
- [ ] Missing X-Visitor-ID header returns appropriate error
- [ ] Workspace isolation is maintained for guests
- [ ] Authenticated users cannot access guest conversations
- [ ] Guest conversations can be deleted
- [ ] Frontend example works correctly
- [ ] Database schema supports guest mode correctly
- [ ] Performance is acceptable under load

## Common Issues (常见问题)

### Issue: "Guest users must provide X-Visitor-ID header"

**Solution**: Ensure the header is included and not empty:
```javascript
headers: {
  'X-Visitor-ID': visitorId || crypto.randomUUID()
}
```

### Issue: Guest conversations not persisting

**Solution**: Verify the same visitor_id is being used across requests. Check localStorage:
```javascript
console.log(localStorage.getItem('dingent_visitor_id'));
```

### Issue: 403 Forbidden when accessing conversation

**Solution**: Ensure the visitor_id matches the one used to create the conversation.
