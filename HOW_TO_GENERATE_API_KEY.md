# 🔑 How to Generate/Update API Key for Paper Trading

## 📋 **Problem**

When accessing Orderbook, Tradebook, or Positions in paper trading mode, you may see:
- "Invalid openalgo apikey" error
- "No API key found for analyze/paper trading mode"
- Redirect to login page

## ✅ **Solution: Generate API Key**

### **Step 1: Login to OpenAlgo**
1. Go to: `http://localhost:5000/auth/login`
2. Enter your username and password
3. Click "Sign in"

### **Step 2: Navigate to API Keys**
1. After login, click on **"API Key"** in the navigation menu
2. Or go directly to: `http://localhost:5000/apikey`

### **Step 3: Generate API Key**
1. Click **"Generate API Key"** or **"Create API Key"** button
2. The API key will be displayed **ONCE** - copy it immediately!
3. Save it securely (you won't be able to see it again)

### **Step 4: Verify API Key**
1. The API key should now be stored in the database
2. Try accessing Orderbook, Tradebook, or Positions again
3. They should now work correctly

## 🔄 **If API Key Already Exists**

If you already have an API key but it's not working:

1. Go to **Settings → API Keys**
2. Click **"Regenerate API Key"** or **"Update API Key"**
3. Copy the new API key
4. Update any strategies or scripts using the old key

## ⚠️ **Important Notes**

- **API Key is shown only once** - save it immediately!
- **API Key is required** for paper trading mode
- **API Key is different** from broker authentication tokens
- **API Key is used** for sandbox/paper trading operations

## 🧪 **Testing**

After generating the API key:
1. ✅ Orderbook should load without errors
2. ✅ Tradebook should load without errors
3. ✅ Positions should load without errors
4. ✅ No more "Invalid openalgo apikey" errors

## 📝 **Troubleshooting**

### **Still Getting "Invalid API Key" Error?**
1. Check if API key was copied correctly (no extra spaces)
2. Regenerate the API key
3. Clear browser cache and cookies
4. Logout and login again

### **Still Redirecting to Login?**
1. Check server logs for session errors
2. Verify session cookie is set in browser
3. Try accessing `/analyzer` first to verify session

## ✅ **Status**

After generating the API key, all paper trading routes should work correctly!




