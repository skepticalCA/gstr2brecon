# Streamlit Cloud Deployment Guide
## GST Reconciliation Pro v2.0

This guide provides step-by-step instructions for deploying the GST Reconciliation Pro application on Streamlit Cloud.

---

## 📋 Pre-Deployment Checklist

- [ ] GitHub account created
- [ ] Streamlit Cloud account created (free at share.streamlit.io)
- [ ] All files ready:
  - `gst_reconciliation_pro.py`
  - `requirements.txt`
  - `README.md`
  - `.streamlit/config.toml` (optional)

---

## 🚀 Deployment Steps

### Step 1: Prepare Your GitHub Repository

#### 1.1 Create a New Repository on GitHub

1. Go to [github.com](https://github.com)
2. Click the "+" icon → "New repository"
3. Repository name: `gst-reconciliation-pro`
4. Description: "GST Reconciliation Tool with 8-Layer Algorithm"
5. Keep it **Public** (required for free Streamlit hosting)
6. ✅ Initialize with README (or uncheck if you have your own)
7. Click "Create repository"

#### 1.2 Upload Files to GitHub

**Option A: Using GitHub Web Interface**

1. In your repository, click "Add file" → "Upload files"
2. Drag and drop all files:
   - `gst_reconciliation_pro.py`
   - `requirements.txt`
   - `README.md`
3. For `.streamlit/config.toml`:
   - Click "Add file" → "Create new file"
   - Type `.streamlit/config.toml` as filename
   - Paste the config content
4. Add commit message: "Initial commit - GST Reconciliation Pro"
5. Click "Commit changes"

**Option B: Using Git Command Line**

```bash
# Navigate to your project directory
cd /path/to/your/project

# Initialize git repository
git init

# Add all files
git add .

# Commit files
git commit -m "Initial commit - GST Reconciliation Pro"

# Add your GitHub repository as remote
git remote add origin https://github.com/YOUR_USERNAME/gst-reconciliation-pro.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Streamlit Cloud

#### 2.1 Sign Up for Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "Sign up with GitHub"
3. Authorize Streamlit to access your GitHub account
4. Complete your profile

#### 2.2 Deploy Your App

1. Click "New app" button
2. Fill in deployment settings:
   - **Repository**: Select `YOUR_USERNAME/gst-reconciliation-pro`
   - **Branch**: `main`
   - **Main file path**: `gst_reconciliation_pro.py`
   - **App URL**: Choose a custom URL (e.g., `gst-reconciliation-nlc`)
3. Click "Deploy!"

#### 2.3 Wait for Deployment

- Initial deployment takes 2-5 minutes
- You'll see a build log showing installation progress
- Once complete, your app will automatically launch

---

## ✅ Post-Deployment Configuration

### Update App Settings (Optional)

1. In Streamlit Cloud dashboard, click on your app
2. Click "⚙️ Settings"
3. Configure:

**Secrets** (if needed for API keys):
```toml
# Not currently required for this app
# Add any sensitive configuration here
```

**Python Version**:
- Recommended: 3.11 (latest stable)

**Resources**:
- Free tier: 1 GB RAM, 1 CPU
- Upgrade if processing very large files (>50MB)

---

## 🔧 Troubleshooting Deployment Issues

### Issue 1: Deployment Fails with "Requirements Error"

**Error**: `ERROR: Could not find a version that satisfies the requirement...`

**Solution**:
1. Check `requirements.txt` has correct package names
2. Try pinning versions less strictly:
   ```
   streamlit>=1.28.0
   pandas>=2.0.0
   ```
3. Re-deploy the app

### Issue 2: App Shows "Module Not Found"

**Error**: `ModuleNotFoundError: No module named 'rapidfuzz'`

**Solution**:
1. Ensure `requirements.txt` includes the module
2. Check file is named exactly `requirements.txt` (not `requirement.txt`)
3. Restart the app from Streamlit Cloud dashboard

### Issue 3: File Upload Size Limit

**Error**: File upload fails for large files

**Solution**:
1. Check `.streamlit/config.toml` has:
   ```toml
   [server]
   maxUploadSize = 200
   ```
2. If still failing, upgrade Streamlit Cloud plan
3. Or process files in smaller batches

### Issue 4: App Runs Slowly

**Symptoms**: App takes long to load or process files

**Solution**:
1. Verify `@st.cache_data` decorators are present
2. Consider upgrading to paid tier for more resources
3. Optimize data processing:
   - Process in chunks
   - Reduce high tolerance setting
   - Disable fuzzy matching for very large files

### Issue 5: Changes Not Reflecting

**Symptoms**: Updated code doesn't show in deployed app

**Solution**:
1. Ensure changes are pushed to GitHub:
   ```bash
   git add .
   git commit -m "Update: description"
   git push
   ```
2. In Streamlit Cloud, click "Reboot app"
3. Clear browser cache

---

## 🔒 Security Best Practices

### 1. Manage Sensitive Data

**Never commit to GitHub**:
- Actual GST data files
- API keys or passwords
- Personal information

Use Streamlit Secrets for sensitive config:
```python
# In your app code
import streamlit as st
api_key = st.secrets["api_key"]
```

### 2. Access Control

For private apps:
1. Upgrade to Streamlit Cloud Teams/Enterprise
2. Configure allowed email domains
3. Enable SSO if available

### 3. Data Privacy

- All file processing happens in-memory
- No persistent storage on server
- Each user session is isolated
- Files are deleted after session ends

---

## 📊 Monitoring Your App

### App Analytics (Available in Settings)

1. **View Count**: Number of unique visitors
2. **Session Duration**: Average time users spend
3. **Error Logs**: Track any runtime errors
4. **Resource Usage**: Monitor CPU and memory

### Setting Up Alerts

1. Go to app settings
2. Enable email notifications for:
   - App crashes
   - High error rates
   - Resource warnings

---

## 🔄 Updating Your Deployed App

### Method 1: GitHub Web Interface

1. Navigate to file in GitHub
2. Click pencil icon to edit
3. Make changes
4. Commit directly to main branch
5. App auto-deploys in 1-2 minutes

### Method 2: Git Command Line

```bash
# Make changes to your local files
# Then:
git add .
git commit -m "Feature: Added new reconciliation layer"
git push

# App auto-updates within 2 minutes
```

### Method 3: Using Branches (Recommended for Major Changes)

```bash
# Create feature branch
git checkout -b feature/new-analytics

# Make and test changes locally
streamlit run gst_reconciliation_pro.py

# Commit changes
git add .
git commit -m "Add advanced analytics"

# Push to GitHub
git push origin feature/new-analytics

# Create Pull Request on GitHub
# After review, merge to main
# App auto-deploys from main branch
```

---

## 📈 Scaling Considerations

### When to Upgrade

**Free Tier Limits**:
- 1 GB RAM
- 1 CPU core
- 1 GB storage
- 3 apps maximum

**Consider upgrading if**:
- Processing files >50 MB regularly
- Users >100 concurrent
- Need private app deployment
- Require custom domain
- Need priority support

### Performance Optimization

**For Large Datasets**:

```python
# Add batch processing
CHUNK_SIZE = 1000

def process_large_file(df):
    chunks = [df[i:i+CHUNK_SIZE] for i in range(0, len(df), CHUNK_SIZE)]
    results = []
    
    for i, chunk in enumerate(chunks):
        st.info(f"Processing chunk {i+1}/{len(chunks)}")
        result = process_chunk(chunk)
        results.append(result)
    
    return pd.concat(results)
```

---

## 🎯 Custom Domain Setup

### Using Streamlit Cloud (Teams/Enterprise)

1. Upgrade to paid plan
2. Go to app settings
3. Add custom domain (e.g., gst.nlcindia.com)
4. Follow DNS configuration steps
5. SSL certificate auto-generated

### Alternative: Use CNAME

```
# Add DNS record:
Type: CNAME
Name: gst
Value: your-app-name.streamlit.app
```

---

## 🆘 Getting Help

### Streamlit Community

- **Forum**: [discuss.streamlit.io](https://discuss.streamlit.io)
- **Documentation**: [docs.streamlit.io](https://docs.streamlit.io)
- **GitHub Issues**: [github.com/streamlit/streamlit](https://github.com/streamlit/streamlit)

### App-Specific Support

- Check error logs in Streamlit Cloud dashboard
- Review GitHub commits for recent changes
- Test locally before deploying: `streamlit run gst_reconciliation_pro.py`

---

## ✅ Deployment Checklist

Before going live, verify:

- [ ] All files pushed to GitHub
- [ ] App deploys without errors
- [ ] File upload works (test with sample files)
- [ ] All 8 layers execute correctly
- [ ] Charts render properly
- [ ] Download functionality works
- [ ] Mobile view is responsive
- [ ] Error handling works (test with invalid files)
- [ ] Performance is acceptable (<30 seconds for typical files)
- [ ] Documentation is accessible
- [ ] Team has access to app URL

---

## 📝 Maintenance Schedule

### Weekly
- Check error logs
- Monitor performance metrics
- Review user feedback

### Monthly
- Update dependencies if needed
- Review and optimize slow queries
- Test with latest data formats

### Quarterly
- Major feature updates
- Security audit
- Performance optimization review

---

## 🎉 You're All Set!

Your GST Reconciliation Pro app is now live and accessible to users worldwide!

**Share your app URL**:
```
https://gst-reconciliation-nlc.streamlit.app
```

**Need to make changes?**
Just push to GitHub - your app auto-updates!

**Questions?**
Check the [Streamlit Community Forum](https://discuss.streamlit.io)

---

**Document Version:** 1.0  
**Last Updated:** February 2026  
**Maintained by:** IT Department, NLC India Limited
