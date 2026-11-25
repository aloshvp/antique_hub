"""
Module 15: Performance & Load Benchmark Script for Antique Hub.
Tests marketplace response times and database query efficiency under load:
1. Bulk generates 500 authentic antique items and inventory stock records.
2. Benchmarks core buyer search and discovery endpoints:
   - Keyword text search (e.g. 'Bronze', 'Dynasty', 'Coin', 'Sword', 'Vase')
   - Category filtering
   - Price range filtering
   - Sorting (price ascending / descending, newest)
   - Multi-parameter faceted filtering with pagination
3. Measures latency (Min, Avg, Max in milliseconds) and throughput (req/sec).
4. Verifies response times meet the web performance benchmark (< 200 ms).
5. Cleans up all 500 test records to keep database clean.

Usage:
    python scripts/performance_test.py
"""

import os
import sys
import time
import random
from decimal import Decimal

# Ensure UTF-8 output on Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Setup Django Environment
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)
sys.path.insert(0, project_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'antique_hub.settings')

import django
django.setup()

from django.test.utils import setup_test_environment
setup_test_environment()

from django.conf import settings
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import connection

from accounts.models import Role, UserProfile
from catalog.models import Category, SubCategory, Item
from inventory.models import Stock


TOTAL_PERF_ITEMS = 500
BENCHMARK_ITERATIONS = 10
PERF_PREFIX = "PERF-ITEM-"

PERIODS = [
    "Chola Dynasty", "Mughal Era", "Gupta Empire", "Vijayanagara Empire",
    "Maratha Empire", "British Raj", "Pallava Dynasty", "Maurya Empire"
]

MATERIALS = [
    "Lost-Wax Bronze", "Carved Sandalwood", "Damascene Steel", "Hand-Beaten Brass",
    "Gilded Copper", "Carved Teakwood", "Terracotta", "Pure Silver"
]

ARTIFACT_TYPES = [
    "Temple Bell", "Ritual Vessel", "Ceremonial Sword", "Royal Coin",
    "Sculpted Deity", "Astrolabe", "Carved Chest", "Oil Lamp"
]


class PerformanceBenchmarkRunner:
    """Executes high-scale item generation, search latency benchmarks, and cleanup."""

    def __init__(self):
        self.client = Client()
        self.seller_user = None
        self.categories = []
        self.subcategories = []

    def setup_data(self):
        print(f"\n[1/4] Preparing test environment & seller account...")
        seller_role, _ = Role.objects.get_or_create(role='Seller')
        self.seller_user, _ = User.objects.get_or_create(
            username='perf_test_seller',
            defaults={'email': 'perf_seller@antiquehub.test'}
        )
        self.seller_user.set_password('PerfPass123!')
        self.seller_user.save()

        UserProfile.objects.get_or_create(
            login=self.seller_user,
            defaults={
                'role': seller_role,
                'username': 'perf_test_seller',
                'contactname': 'Performance Benchmark Seller',
                'phone': '9900000000',
                'email': 'perf_seller@antiquehub.test',
                'status': 'Active'
            }
        )

        # Setup sample categories
        cat_names = ["Ancient Bronzes", "Royal Weapons", "Numismatics", "Temple Antiquities"]
        for cname in cat_names:
            cat, _ = Category.objects.get_or_create(category=cname)
            self.categories.append(cat)
            subcat, _ = SubCategory.objects.get_or_create(category=cat, subcategory=f"{cname} Fine Artifacts")
            self.subcategories.append(subcat)

        print(f"[2/4] Bulk generating {TOTAL_PERF_ITEMS} antique listings & stock records...")
        start_gen = time.perf_counter()

        items_to_create = []
        now = timezone.now()

        for i in range(1, TOTAL_PERF_ITEMS + 1):
            period = random.choice(PERIODS)
            material = random.choice(MATERIALS)
            atype = random.choice(ARTIFACT_TYPES)
            cat = random.choice(self.categories)
            subcat = self.subcategories[self.categories.index(cat)]

            price = Decimal(random.randint(5000, 450000))
            age = random.randint(120, 1400)

            title = f"{period} {material} {atype} #{i:04d}"
            code = f"{PERF_PREFIX}{i:04d}"

            item = Item(
                seller=self.seller_user,
                item=code,
                title=title,
                category=cat,
                subcategory=subcat,
                years_old=age,
                origin=f"Historic {period} Region",
                description=f"Authentic artifact crafted from {material}. Preserved from the {period} era. Catalog ref {code}.",
                price=price,
                status='Available'
            )
            items_to_create.append(item)

        # Bulk create items
        created_items = Item.objects.bulk_create(items_to_create, batch_size=250)

        # Bulk create corresponding stocks
        stocks_to_create = [
            Stock(
                item=it,
                tot_arr_stock=5,
                cur_stock=random.randint(1, 5),
                stockdate=now,
                status='Available'
            )
            for it in created_items
        ]
        Stock.objects.bulk_create(stocks_to_create, batch_size=250)

        gen_time = time.perf_counter() - start_gen
        total_items_db = Item.objects.count()
        print(f"      Created {len(created_items)} items in {gen_time:.2f}s. (Total Items in DB: {total_items_db})")

    def benchmark_query(self, scenario_name, params, iterations=BENCHMARK_ITERATIONS):
        """Runs a search/filter request multiple times and calculates timing metrics."""
        url = reverse('catalog:item_list')
        latencies = []
        result_count = 0

        # Warm-up request
        warmup_res = self.client.get(url, params)
        assert warmup_res.status_code == 200, f"Scenario '{scenario_name}' failed with status {warmup_res.status_code}"

        for _ in range(iterations):
            t0 = time.perf_counter()
            res = self.client.get(url, params)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)

        min_ms = min(latencies)
        avg_ms = sum(latencies) / len(latencies)
        max_ms = max(latencies)
        rps = 1000.0 / avg_ms if avg_ms > 0 else 0

        # Extract result count from response context
        if warmup_res.context and 'page_obj' in warmup_res.context:
            page_obj = warmup_res.context['page_obj']
            if hasattr(page_obj, 'paginator'):
                result_count = page_obj.paginator.count

        return {
            'scenario': scenario_name,
            'params': str(params),
            'min_ms': min_ms,
            'avg_ms': avg_ms,
            'max_ms': max_ms,
            'rps': rps,
            'results': result_count,
            'status': 'PASS' if avg_ms < 200.0 else 'WARN'
        }

    def run_benchmarks(self):
        print(f"\n[3/4] Running marketplace search & filter benchmarks ({BENCHMARK_ITERATIONS} iterations each)...")
        cat_id = self.categories[0].pk

        test_scenarios = [
            ("All Items Marketplace (Default Page 1)", {}),
            ("Full-Text Keyword Search ('Bronze')", {'q': 'Bronze'}),
            ("Full-Text Keyword Search ('Chola')", {'q': 'Chola'}),
            ("Full-Text Keyword Search ('Sword')", {'q': 'Sword'}),
            ("Category Filtering ('Ancient Bronzes')", {'category_id': str(cat_id)}),
            ("Price Range Filtering (Rs. 10,000 - 50,000)", {'min_price': '10000', 'max_price': '50000'}),
            ("Price Sorting Ascending", {'sort': 'price_asc'}),
            ("Price Sorting Descending", {'sort': 'price_desc'}),
            ("Combined Search + Category + Sort", {'q': 'Dynasty', 'category_id': str(cat_id), 'sort': 'price_asc'}),
            ("Deep Pagination (Page 5)", {'page': '5'}),
        ]

        results = []
        for name, params in test_scenarios:
            metrics = self.benchmark_query(name, params)
            results.append(metrics)
            print(f"      - {name:<46}: Avg: {metrics['avg_ms']:>6.2f} ms | Min: {metrics['min_ms']:>6.2f} ms | Max: {metrics['max_ms']:>6.2f} ms | {metrics['results']:>3} results")

        return results

    def print_report_table(self, results):
        print("\n" + "=" * 100)
        print("   ANTIQUE HUB - MODULE 15 PERFORMANCE & SEARCH BENCHMARK REPORT (500 ITEMS LOAD)")
        print("=" * 100)
        header = f"| {'Test Scenario':<42} | {'Matches':<7} | {'Min (ms)':<8} | {'Avg (ms)':<8} | {'Max (ms)':<8} | {'Throughput':<11} | {'SLA (<200ms)':<11} |"
        sep = f"|{'-' * 44}|{'-' * 9}|{'-' * 10}|{'-' * 10}|{'-' * 10}|{'-' * 13}|{'-' * 13}|"
        print(header)
        print(sep)

        all_passed = True
        for r in results:
            sla_text = "[PASS]" if r['status'] == 'PASS' else "[WARN]"
            if r['status'] != 'PASS':
                all_passed = False
            line = (
                f"| {r['scenario']:<42} | "
                f"{r['results']:<7} | "
                f"{r['min_ms']:>8.2f} | "
                f"{r['avg_ms']:>8.2f} | "
                f"{r['max_ms']:>8.2f} | "
                f"{r['rps']:>7.1f} req/s | "
                f"{sla_text:^11} |"
            )
            print(line)

        print(sep)
        overall_avg = sum(r['avg_ms'] for r in results) / len(results)
        print(f"   OVERALL SEARCH AVERAGE LATENCY: {overall_avg:.2f} ms across all scenarios.")
        if all_passed:
            print("   \033[1;32mPERFORMANCE SLA COMPLIANT: All 10 search operations executed well under 200 ms threshold.\033[0m")
        else:
            print("   \033[1;33mPERFORMANCE NOTE: Some queries exceeded the strict 200 ms threshold.\033[0m")
        print("=" * 100)

    def cleanup(self):
        print("\n[4/4] Cleaning up performance test items & stock records...")
        deleted_stocks, _ = Stock.objects.filter(item__item__startswith=PERF_PREFIX).delete()
        deleted_items, _ = Item.objects.filter(item__startswith=PERF_PREFIX).delete()
        print(f"      Removed {deleted_items} test items and {deleted_stocks} stock rows. Database cleanly restored.")


if __name__ == '__main__':
    runner = PerformanceBenchmarkRunner()
    try:
        runner.setup_data()
        results = runner.run_benchmarks()
        runner.print_report_table(results)
    finally:
        runner.cleanup()
