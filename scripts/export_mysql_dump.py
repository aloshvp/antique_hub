"""
Module 16: Automated MySQL Seed Dump Generator for Antique Hub.
Exports populated database records into an enterprise-grade, self-contained MySQL .sql dump file:
- Uses Django ORM metadata introspection for 100% exact table names and column names.
- Disables FOREIGN_KEY_CHECKS during import to prevent order-dependency issues.
- Sets character set to utf8mb4.
- Generates clean INSERT statements for all core business tables.
- Re-enables FOREIGN_KEY_CHECKS at the conclusion of import.

Usage:
    python scripts/export_mysql_dump.py
"""

import os
import sys
from decimal import Decimal
from datetime import datetime, date

# Ensure UTF-8 output on Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Setup Django Environment
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)
sys.path.insert(0, project_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'antique_hub.settings')

import django
django.setup()

from django.contrib.auth.models import User
from accounts.models import Role, UserProfile
from locations.models import State, District, Location
from catalog.models import Category, SubCategory, Item
from inventory.models import Stock, Discount
from community.models import FAQ, Comment, WatchListed
from orders.models import PurchaseMaster, Purchase
from payments.models import Payment


def sql_format(val):
    if val is None:
        return "NULL"
    elif isinstance(val, bool):
        return "1" if val else "0"
    elif isinstance(val, (int, float, Decimal)):
        return str(val)
    elif isinstance(val, (datetime, date)):
        return f"'{val.strftime('%Y-%m-%d %H:%M:%S') if isinstance(val, datetime) else val.strftime('%Y-%m-%d')}'"
    else:
        escaped = str(val).replace("\\", "\\\\").replace("'", "''").replace("\r", "").replace("\n", "\\n")
        return f"'{escaped}'"


def export_sql():
    output_path = os.path.join(project_dir, 'fixtures', 'seed_data.sql')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print(f"Generating MySQL seed dump to: {output_path}...")

    lines = []
    lines.append("-- ============================================================================")
    lines.append("-- Antique Hub - Master MySQL 8 Database Dump & Seed Data (Module 16)")
    lines.append(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("-- Character Set: utf8mb4 | Collation: utf8mb4_unicode_ci")
    lines.append("-- ============================================================================")
    lines.append("")
    lines.append("SET NAMES utf8mb4;")
    lines.append("SET FOREIGN_KEY_CHECKS = 0;")
    lines.append("SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';")
    lines.append("")

    MODELS_TO_DUMP = [
        User,
        Role,
        State,
        District,
        Location,
        UserProfile,
        Category,
        SubCategory,
        Item,
        Stock,
        Discount,
        FAQ,
        PurchaseMaster,
        Purchase,
        Payment,
        Comment,
        WatchListed,
    ]

    for model in MODELS_TO_DUMP:
        table_name = model._meta.db_table
        fields = model._meta.fields
        columns = [f.column for f in fields]

        records = list(model.objects.all().order_by(model._meta.pk.name))
        lines.append(f"-- ------------------------------------------------------------")
        lines.append(f"-- Data for table `{table_name}` ({len(records)} rows)")
        lines.append(f"-- ------------------------------------------------------------")

        if not records:
            lines.append(f"-- (No rows in `{table_name}`)\n")
            continue

        col_str = ", ".join(f"`{c}`" for c in columns)
        lines.append(f"INSERT INTO `{table_name}` ({col_str}) VALUES")
        val_lines = []
        for r in records:
            vals = [sql_format(getattr(r, f.attname)) for f in fields]
            val_lines.append(f"  ({', '.join(vals)})")
        lines.append(",\n".join(val_lines) + ";\n")

    lines.append("SET FOREIGN_KEY_CHECKS = 1;")
    lines.append("")
    lines.append("-- ============================================================================")
    lines.append("-- End of Antique Hub MySQL Seed Dump")
    lines.append("-- ============================================================================")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

    print(f"[SUCCESS] Exported {len(lines)} lines to fixtures/seed_data.sql ({os.path.getsize(output_path)} bytes).")


if __name__ == '__main__':
    export_sql()
