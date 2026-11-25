"""
Management command to seed 8 comprehensive, domain-accurate FAQs
covering authenticity, shipping, returns, payments, and selling policies.
"""

from django.core.management.base import BaseCommand
from community.models import FAQ

SEED_FAQS = [
    {
        "faq": "How does Antique Hub verify the authenticity and historical provenance of listed relics?",
        "answer": (
            "Every antique artifact cataloged on Antique Hub undergoes a rigorous multi-tier provenance audit "
            "before being made available for acquisition. Sellers must be verified dealers approved by our "
            "heritage curation committee. Listing requirements mandate high-resolution hallmark proof images, "
            "estimated epoch documentation, archaeological origin, and strict compliance with the Antiquities "
            "and Art Treasures Act, 1972. Any artifact displaying signs of contemporary reproduction or questionable "
            "lineage is rejected immediately."
        )
    },
    {
        "faq": "What qualifies an artifact as a genuine antique on Antique Hub?",
        "answer": (
            "In accordance with statutory heritage guidelines and museum conservation benchmarks, items on Antique Hub "
            "must generally be at least 100 years old to be classified as historical antiques. Rare vintage collectibles, "
            "numismatics, and mid-century art objects aged 50 to 99 years may be cataloged under designated vintage "
            "subcategories, provided their provenance, manufacturer hallmarks, and cultural significance are fully documented."
        )
    },
    {
        "faq": "How are fragile antique artifacts packaged to prevent damage during transit?",
        "answer": (
            "We enforce specialized museum-grade packaging standards for all antique shipments. Each piece is cushioned "
            "using acid-free archival tissue, multi-layer high-density shock-absorbing foam, custom-molded interior supports, "
            "and reinforced double-walled corrugated or wooden crates. Fragile glass, terracotta, and bronze relics receive "
            "additional climate-barrier seals to withstand humidity and temperature fluctuations during national transport."
        )
    },
    {
        "faq": "What are the estimated shipping timelines and how can I track my antique order?",
        "answer": (
            "Once an order is confirmed and undergoes pre-dispatch condition verification (within 24 to 48 business hours), "
            "it is dispatched via insured, white-glove logistics partners. Domestic deliveries across India typically arrive "
            "within 3 to 7 business days depending on destination geography. Buyers receive automated dispatch notifications "
            "and can monitor real-time shipping milestones directly on the 'Track Order Status' page."
        )
    },
    {
        "faq": "What is the return and refund policy if an antique arrives damaged or misdescribed?",
        "answer": (
            "Antique Hub provides a 48-hour Buyer Protection guarantee upon recorded delivery. Because antique relics are "
            "irreplaceable, buyers are advised to record a continuous unboxing video upon receipt. If an artifact arrives damaged "
            "in transit or displays material discrepancies from its cataloged description, buyers can initiate an inspection claim. "
            "Upon return and physical verification by our curation team, a 100% full refund is credited back to the original payment source."
        )
    },
    {
        "faq": "What payment methods are supported and how is my financial data protected?",
        "answer": (
            "We accept all major Credit/Debit Cards (Visa, MasterCard, RuPay), Net Banking across 50+ Indian banks, "
            "Unified Payments Interface (UPI), and Cash on Delivery (COD) for eligible regional orders. All digital transactions "
            "are processed through PCI-DSS Level 1 compliant encrypted gateways with 256-bit SSL encryption. In strict compliance "
            "with RBI tokenization rules, raw card numbers and CVVs are never saved on our database servers."
        )
    },
    {
        "faq": "How can an antique dealer or private collector become an approved seller?",
        "answer": (
            "Prospective sellers must register via our Seller Portal, providing their enterprise contact details, verifiable "
            "physical showroom address, state, district, and tax/ID documentation. All new seller profiles are initially assigned "
            "'Pending' status and cannot publish listings until our Administrator conducts a background verification and activates "
            "the account. Once activated, sellers gain full access to upload items, manage stock, and track sales."
        )
    },
    {
        "faq": "What commissions are charged to sellers and when are sales proceeds disbursed?",
        "answer": (
            "Antique Hub operates on a transparent, flat commission model with zero hidden monthly subscription fees. Sellers "
            "receive complete visibility into item totals, applied promotional discounts, and net earnings via their Seller Hub "
            "dashboard. Following successful delivery of the artifact and completion of the 48-hour buyer verification window, sales "
            "proceeds are automatically disbursed directly into the seller's registered bank account within 3 business days."
        )
    }
]


class Command(BaseCommand):
    help = "Seeds 8 comprehensive FAQs about authenticity, shipping, returns, payments, and selling."

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for item in SEED_FAQS:
            faq_obj, created = FAQ.objects.get_or_create(
                faq=item["faq"],
                defaults={"answer": item["answer"]}
            )
            if created:
                created_count += 1
            else:
                faq_obj.answer = item["answer"]
                faq_obj.save()
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded FAQs! Created: {created_count}, Updated: {updated_count}, Total in DB: {FAQ.objects.count()}"
            )
        )
