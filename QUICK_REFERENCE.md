# GST Reconciliation Pro - Quick Reference Card

## 🚀 Quick Start (3 Simple Steps)

### 1️⃣ Upload Files
- **CIS File**: Your Credit Information Statement (Excel)
- **GSTR-2B File**: Downloaded from GST Portal (Excel)

### 2️⃣ Adjust Settings (Optional)
- **Standard Tolerance**: ₹2 (for most matches)
- **High Tolerance**: ₹50 (for larger variances)

### 3️⃣ Click "Run Reconciliation"
- Watch real-time progress
- View instant results
- Download reconciled data

---

## 📊 Understanding the Results

### Match Status Colors
- 🟢 **Green Row** = Successfully Matched
- 🔴 **Red Row** = Unmatched (not found in GSTR-2B)
- 🟡 **Yellow Row** = Time Barred (date before 31-Mar-2024)

### Result Columns
- **Matching Status**: Matched / Unmatched
- **Match Category**: Which layer found the match (1-8)
- **GSTR 2B Key**: Reference to matched GSTR-2B record
- **Detailed Remark**: Explanation of match criteria
- **Short Remark**: Quick summary

---

## 🔄 8 Reconciliation Layers Explained

| Layer | What It Matches | Example |
|-------|----------------|---------|
| 1. Strict | GSTIN + Invoice + Taxable + Tax | Exact match, no variance |
| 2. Grand Total | GSTIN + Invoice + Grand Total | Tax split differs slightly |
| 3. High Tolerance | GSTIN + Invoice + Amount (±₹50) | Rounding differences |
| 4. Numeric Only | GSTIN + Numbers from Invoice | `GST/01` matches `01` |
| 5. Last 4 Digits | GSTIN + Last 4 digits | `WB-0995` matches `0995` |
| 6. PAN Level | PAN + Invoice + Amount | Different state branches |
| 7. Fuzzy | GSTIN + Similar Invoice (85%+) | `9855` matches `9885` (typo) |
| 8. Reverse Club | 1 CIS = Multiple G2B entries | Split invoices combined |

---

## ⚙️ When to Adjust Settings

### Increase High Tolerance (Layer 3)
**When**: Many records show small amount differences
**Try**: ₹100 or ₹200
**Example**: Rounding differences, forex conversions

### Decrease Tolerances
**When**: You want stricter matching only
**Try**: ₹0.50 or ₹1.00
**Caution**: May reduce match rate

### Disable Fuzzy Matching
**When**: Processing very large files (>10,000 records)
**Benefit**: Faster processing
**Trade-off**: May miss typo-based matches

---

## 📥 Download Options

### 📊 Excel File (Recommended)
- **Contains**: 
  - CIS Reconciled (main results)
  - GSTR2B Mapped (with CIS references)
  - Statistics (layer-wise summary)
  - Audit Log (detailed match trail)
- **Best For**: Final submission, archival

### 📄 CSV File
- **Contains**: CIS reconciled data only
- **Best For**: Further analysis in other tools

### 📋 JSON Audit Log
- **Contains**: Detailed audit trail
- **Best For**: Technical review, debugging

---

## 🔍 Common Scenarios & Solutions

### Scenario 1: Low Match Rate (<80%)

**Check**:
1. File formats correct?
2. GSTIN format valid (15 characters)?
3. Invoice numbers not blank?
4. Amounts in numeric format?

**Try**:
1. Increase high tolerance to ₹100
2. Check invoice number format consistency
3. Review sample unmatched records in Analytics tab

### Scenario 2: Invoice Format Differences

**Symptoms**: CIS has `INV-001`, GSTR-2B has `001`

**Solution**: Layers 4 & 5 handle this automatically
- Layer 4 extracts numeric part only
- Layer 5 matches last 4 digits

### Scenario 3: Head Office vs Branch

**Symptoms**: Same PAN, different GSTIN suffixes

**Solution**: Layer 6 handles PAN-level matching
- Ignores last 5 characters of GSTIN
- Matches on first 10 characters (PAN)

### Scenario 4: Split Invoices

**Symptoms**: 1 invoice in CIS, multiple lines in GSTR-2B

**Solution**: Layer 8 (Reverse Clubbing)
- Automatically groups GSTR-2B records
- Compares summed amounts

---

## 📈 Analytics Tab Features

### Key Metrics Dashboard
- Total records processed
- Match rate percentage
- Layer-wise statistics
- Amount distribution charts

### Mismatch Analysis
- Invoice format issues count
- GSTIN validation errors
- Time-barred records
- Sample unmatched records table

### Visual Charts
- 🥧 Match Rate Pie Chart
- 📊 Layer Performance Bar Chart
- 📈 Amount Distribution Histogram

---

## ⚠️ Common Errors & Fixes

### Error: "Missing required column"
**Fix**: Ensure your Excel has these columns:
- CIS: SupplierGSTIN, DocumentNumber, DocumentDate
- GSTR-2B: GSTIN of supplier, Invoice number, Invoice Date

### Error: File upload fails
**Fix**: 
- Use .xlsx format only (not .xls or .csv)
- File size must be <200 MB
- Remove any password protection

### Error: "Processing taking too long"
**Fix**:
- For files >10,000 records, disable fuzzy matching
- Process in smaller date ranges
- Close other browser tabs

---

## 💡 Pro Tips

### Tip 1: Pre-Process Your Data
Before upload:
- Remove duplicate rows
- Ensure GSTIN is 15 characters
- Check invoice numbers are not blank
- Verify amounts are numeric (remove currency symbols)

### Tip 2: Start Conservative
First run:
- Use default settings (₹2, ₹50)
- Review results in Analytics
- Adjust tolerances based on findings

### Tip 3: Use Audit Trail
For important reconciliations:
- Enable "Generate Audit Log"
- Download complete audit trail
- Keep for compliance records

### Tip 4: Batch Processing
For very large datasets:
- Split by month or quarter
- Process each batch separately
- Combine results in Excel

---

## 🎯 Best Practices

### Before Reconciliation
✅ Validate file formats
✅ Check for blank cells
✅ Remove test/dummy data
✅ Verify date formats (DD/MM/YYYY)

### During Reconciliation
✅ Don't close browser window
✅ Watch for error messages
✅ Monitor progress indicator
✅ Note any warnings shown

### After Reconciliation
✅ Review Analytics dashboard
✅ Check sample unmatched records
✅ Download all results
✅ Verify critical matches manually

---

## 📞 Need Help?

### Self-Service Resources
1. **Help Tab**: Built-in documentation
2. **Analytics Tab**: Mismatch analysis
3. **Sample Records**: Review examples

### Technical Support
- **Email**: support@nlcindia.com
- **IT Helpdesk**: Ext. 1234
- **Working Hours**: 9 AM - 6 PM IST

---

## 📋 Checklist for First-Time Users

- [ ] Excel files ready (.xlsx format)
- [ ] Files contain all required columns
- [ ] GSTIN format validated (15 chars)
- [ ] Invoice numbers present
- [ ] Amounts in numeric format
- [ ] Date format consistent
- [ ] No merged cells in data area
- [ ] Files size under 200 MB
- [ ] Browser: Chrome/Firefox (recommended)
- [ ] Stable internet connection

---

## 🔑 Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Refresh page | `Ctrl + R` or `F5` |
| Clear cache | `C` (when focused) |
| Download results | Click download button |
| Expand all sections | Click expanders |

---

## 📊 File Size Guidelines

| Record Count | Expected Time | Recommended Settings |
|-------------|--------------|---------------------|
| < 1,000 | 5-10 seconds | All layers enabled |
| 1,000 - 5,000 | 15-30 seconds | All layers enabled |
| 5,000 - 10,000 | 30-60 seconds | All layers enabled |
| > 10,000 | 1-3 minutes | Disable fuzzy matching |

---

## ✅ Success Indicators

**Good Match Rate**: >85%
**Acceptable Match Rate**: 70-85%
**Review Required**: <70%

If match rate <70%:
1. Check data quality
2. Review invoice formats
3. Increase tolerances
4. Contact support

---

**Quick Reference v1.0**  
**For**: GST Reconciliation Pro v2.0  
**Last Updated**: February 2026

---

💡 **Remember**: When in doubt, start with default settings and review the Analytics tab for insights!
