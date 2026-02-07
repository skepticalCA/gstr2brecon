"""
Sample Data Generator for GST Reconciliation Pro
Generates realistic test data for CIS and GSTR-2B files
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

def generate_gstin():
    """Generate a realistic-looking GSTIN"""
    state_codes = ['01', '09', '19', '24', '27', '29', '33', '36']
    state = random.choice(state_codes)
    pan = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=5))
    pan += ''.join(random.choices('0123456789', k=4))
    pan += random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    entity = random.choice('123456789')
    check = random.choice('Z123456789')
    return f"{state}{pan}{entity}{check}"

def generate_invoice_number(prefix_style='mixed'):
    """Generate various invoice number formats"""
    if prefix_style == 'numeric':
        return str(random.randint(1000, 9999))
    elif prefix_style == 'alpha':
        return f"INV-{random.randint(100, 999)}"
    elif prefix_style == 'state':
        states = ['WB', 'MH', 'DL', 'TN', 'KA']
        return f"{random.choice(states)}-{random.randint(1000, 9999)}"
    else:  # mixed
        styles = ['numeric', 'alpha', 'state']
        return generate_invoice_number(random.choice(styles))

def generate_date(start_date, end_date):
    """Generate random date between start and end"""
    time_between = end_date - start_date
    days_between = time_between.days
    random_days = random.randint(0, days_between)
    return start_date + timedelta(days=random_days)

def generate_amount():
    """Generate realistic invoice amounts"""
    # Most invoices are small, some are large
    if random.random() < 0.7:
        return round(random.uniform(5000, 50000), 2)
    elif random.random() < 0.9:
        return round(random.uniform(50000, 200000), 2)
    else:
        return round(random.uniform(200000, 1000000), 2)

def create_sample_data(num_records=100, mismatch_rate=0.15):
    """
    Create sample CIS and GSTR-2B data
    
    Parameters:
    - num_records: Number of records to generate
    - mismatch_rate: Percentage of records that should be mismatches (0-1)
    """
    
    print(f"Generating {num_records} sample records...")
    
    # Date range for invoices
    start_date = datetime(2024, 4, 1)
    end_date = datetime(2025, 1, 31)
    
    # Generate supplier GSTINs (10-20 unique suppliers)
    num_suppliers = min(20, max(10, num_records // 5))
    suppliers = {
        generate_gstin(): f"Supplier_{i+1}" 
        for i in range(num_suppliers)
    }
    
    cis_records = []
    g2b_records = []
    
    matched_records = int(num_records * (1 - mismatch_rate))
    
    # Generate matched records
    for i in range(matched_records):
        gstin = random.choice(list(suppliers.keys()))
        invoice_num = generate_invoice_number()
        invoice_date = generate_date(start_date, end_date)
        taxable_value = generate_amount()
        
        # Randomly choose tax type (IGST or CGST+SGST)
        if random.random() < 0.5:
            # IGST (interstate)
            tax_rate = random.choice([5, 12, 18, 28])
            igst = round(taxable_value * tax_rate / 100, 2)
            cgst = 0
            sgst = 0
        else:
            # CGST + SGST (intrastate)
            tax_rate = random.choice([5, 12, 18, 28])
            igst = 0
            cgst = round(taxable_value * tax_rate / 200, 2)
            sgst = round(taxable_value * tax_rate / 200, 2)
        
        # Add variation for different layer testing
        variation_type = random.random()
        
        if variation_type < 0.6:
            # Layer 1 & 2: Exact match
            cis_inv = invoice_num
            g2b_inv = invoice_num
            g2b_taxable = taxable_value
            g2b_igst, g2b_cgst, g2b_sgst = igst, cgst, sgst
            
        elif variation_type < 0.7:
            # Layer 3: Small amount difference
            cis_inv = invoice_num
            g2b_inv = invoice_num
            g2b_taxable = taxable_value + round(random.uniform(-30, 30), 2)
            g2b_igst, g2b_cgst, g2b_sgst = igst, cgst, sgst
            
        elif variation_type < 0.8:
            # Layer 4: Numeric only
            prefix = random.choice(['INV/', 'GST/', 'BIL/'])
            cis_inv = f"{prefix}{invoice_num}"
            g2b_inv = invoice_num
            g2b_taxable = taxable_value
            g2b_igst, g2b_cgst, g2b_sgst = igst, cgst, sgst
            
        elif variation_type < 0.9:
            # Layer 7: Fuzzy match (typo)
            num_part = ''.join(filter(str.isdigit, invoice_num))
            if num_part and len(num_part) >= 4:
                # Introduce single digit typo
                num_list = list(num_part)
                idx = random.randint(0, len(num_list)-1)
                num_list[idx] = str((int(num_list[idx]) + random.randint(1, 2)) % 10)
                typo_num = ''.join(num_list)
                cis_inv = invoice_num
                g2b_inv = typo_num if random.random() < 0.5 else f"INV-{typo_num}"
            else:
                cis_inv = invoice_num
                g2b_inv = invoice_num
            g2b_taxable = taxable_value
            g2b_igst, g2b_cgst, g2b_sgst = igst, cgst, sgst
            
        else:
            # Layer 6: PAN level (different GSTIN, same PAN)
            cis_inv = invoice_num
            g2b_inv = invoice_num
            # Change last 5 characters of GSTIN
            pan = gstin[:10]
            gstin = f"{pan}{''.join(random.choices('123456789Z', k=5))}"
            g2b_taxable = taxable_value
            g2b_igst, g2b_cgst, g2b_sgst = igst, cgst, sgst
        
        # CIS Record
        cis_records.append({
            'SupplierGSTIN': gstin,
            'DocumentNumber': cis_inv,
            'DocumentDate': invoice_date.strftime('%d/%m/%Y'),
            'TaxableValue': taxable_value,
            'IntegratedTaxAmount': igst,
            'CentralTaxAmount': cgst,
            'StateUT TaxAmount': sgst,
            'SupplierName': suppliers.get(gstin[:10] + '00000', 'Unknown')[:gstin[:10]]
        })
        
        # GSTR-2B Record
        g2b_records.append({
            'GSTIN of supplier': gstin,
            'Invoice number': g2b_inv,
            'Invoice Date': invoice_date.strftime('%d/%m/%Y'),
            'Taxable Value (₹)': g2b_taxable,
            'Integrated Tax(₹)': g2b_igst,
            'Central Tax(₹)': g2b_cgst,
            'State/UT Tax(₹)': g2b_sgst
        })
    
    # Generate unmatched records (only in CIS)
    unmatched_records = num_records - matched_records
    for i in range(unmatched_records):
        gstin = random.choice(list(suppliers.keys()))
        invoice_num = generate_invoice_number()
        invoice_date = generate_date(start_date, end_date)
        taxable_value = generate_amount()
        
        # Randomly choose tax type
        if random.random() < 0.5:
            tax_rate = random.choice([5, 12, 18, 28])
            igst = round(taxable_value * tax_rate / 100, 2)
            cgst = 0
            sgst = 0
        else:
            tax_rate = random.choice([5, 12, 18, 28])
            igst = 0
            cgst = round(taxable_value * tax_rate / 200, 2)
            sgst = round(taxable_value * tax_rate / 200, 2)
        
        cis_records.append({
            'SupplierGSTIN': gstin,
            'DocumentNumber': invoice_num,
            'DocumentDate': invoice_date.strftime('%d/%m/%Y'),
            'TaxableValue': taxable_value,
            'IntegratedTaxAmount': igst,
            'CentralTaxAmount': cgst,
            'StateUT TaxAmount': sgst,
            'SupplierName': suppliers.get(gstin[:10] + '00000', 'Unknown')[:gstin[:10]]
        })
    
    # Add some reverse clubbing scenarios (Layer 8)
    # Take 5% of matched records and split them in G2B
    num_split = max(2, int(matched_records * 0.05))
    for i in range(num_split):
        base_record = random.choice(g2b_records[:matched_records])
        
        # Split into 2-3 records
        num_splits = random.randint(2, 3)
        split_amount = base_record['Taxable Value (₹)'] / num_splits
        split_igst = base_record['Integrated Tax(₹)'] / num_splits
        split_cgst = base_record['Central Tax(₹)'] / num_splits
        split_sgst = base_record['State/UT Tax(₹)'] / num_splits
        
        for j in range(num_splits - 1):
            g2b_records.append({
                'GSTIN of supplier': base_record['GSTIN of supplier'],
                'Invoice number': base_record['Invoice number'],
                'Invoice Date': base_record['Invoice Date'],
                'Taxable Value (₹)': round(split_amount, 2),
                'Integrated Tax(₹)': round(split_igst, 2),
                'Central Tax(₹)': round(split_cgst, 2),
                'State/UT Tax(₹)': round(split_sgst, 2)
            })
    
    # Add some time-barred records (before 31 Mar 2024)
    num_time_barred = max(2, int(num_records * 0.05))
    old_start = datetime(2023, 1, 1)
    old_end = datetime(2024, 3, 30)
    
    for i in range(num_time_barred):
        gstin = random.choice(list(suppliers.keys()))
        invoice_num = generate_invoice_number()
        invoice_date = generate_date(old_start, old_end)
        taxable_value = generate_amount()
        
        tax_rate = random.choice([5, 12, 18, 28])
        igst = round(taxable_value * tax_rate / 100, 2)
        
        cis_records.append({
            'SupplierGSTIN': gstin,
            'DocumentNumber': invoice_num,
            'DocumentDate': invoice_date.strftime('%d/%m/%Y'),
            'TaxableValue': taxable_value,
            'IntegratedTaxAmount': igst,
            'CentralTaxAmount': 0,
            'StateUT TaxAmount': 0,
            'SupplierName': suppliers.get(gstin[:10] + '00000', 'Unknown')[:gstin[:10]]
        })
    
    # Create DataFrames
    df_cis = pd.DataFrame(cis_records)
    df_g2b = pd.DataFrame(g2b_records)
    
    # Shuffle records
    df_cis = df_cis.sample(frac=1).reset_index(drop=True)
    df_g2b = df_g2b.sample(frac=1).reset_index(drop=True)
    
    print(f"✅ Generated {len(df_cis)} CIS records")
    print(f"✅ Generated {len(df_g2b)} GSTR-2B records")
    print(f"📊 Expected match rate: ~{(1-mismatch_rate)*100:.0f}%")
    
    return df_cis, df_g2b

def save_sample_files(df_cis, df_g2b, prefix='sample'):
    """Save sample files to Excel"""
    
    cis_filename = f"{prefix}_CIS.xlsx"
    g2b_filename = f"{prefix}_GSTR2B.xlsx"
    
    # Save CIS
    df_cis.to_excel(cis_filename, index=False, engine='openpyxl')
    print(f"💾 Saved: {cis_filename}")
    
    # Save GSTR-2B with proper formatting
    with pd.ExcelWriter(g2b_filename, engine='openpyxl') as writer:
        df_g2b.to_excel(writer, sheet_name='B2B', index=False)
    print(f"💾 Saved: {g2b_filename}")
    
    return cis_filename, g2b_filename

if __name__ == "__main__":
    print("=" * 60)
    print("GST Reconciliation Pro - Sample Data Generator")
    print("=" * 60)
    print()
    
    # Generate small dataset (100 records)
    print("Generating SMALL dataset (100 records)...")
    df_cis_small, df_g2b_small = create_sample_data(num_records=100, mismatch_rate=0.15)
    save_sample_files(df_cis_small, df_g2b_small, prefix='sample_small')
    print()
    
    # Generate medium dataset (500 records)
    print("Generating MEDIUM dataset (500 records)...")
    df_cis_medium, df_g2b_medium = create_sample_data(num_records=500, mismatch_rate=0.20)
    save_sample_files(df_cis_medium, df_g2b_medium, prefix='sample_medium')
    print()
    
    # Generate large dataset (2000 records)
    print("Generating LARGE dataset (2000 records)...")
    df_cis_large, df_g2b_large = create_sample_data(num_records=2000, mismatch_rate=0.25)
    save_sample_files(df_cis_large, df_g2b_large, prefix='sample_large')
    print()
    
    print("=" * 60)
    print("✅ Sample data generation complete!")
    print("=" * 60)
    print()
    print("Files created:")
    print("  1. sample_small_CIS.xlsx + sample_small_GSTR2B.xlsx")
    print("  2. sample_medium_CIS.xlsx + sample_medium_GSTR2B.xlsx")
    print("  3. sample_large_CIS.xlsx + sample_large_GSTR2B.xlsx")
    print()
    print("Use these files to test the GST Reconciliation Pro app!")
