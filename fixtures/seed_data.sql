-- ============================================================================
-- Antique Hub - Master MySQL 8 Database Dump & Seed Data (Module 16)
-- Generated: 2026-10-20 13:48:14
-- Character Set: utf8mb4 | Collation: utf8mb4_unicode_ci
-- ============================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';

-- ------------------------------------------------------------
-- Data for table `auth_user` (10 rows)
-- ------------------------------------------------------------
INSERT INTO `auth_user` (`id`, `password`, `last_login`, `is_superuser`, `username`, `first_name`, `last_name`, `email`, `is_staff`, `is_active`, `date_joined`) VALUES
  (1, 'pbkdf2_sha256$1500000$KBHcjuHYLKi8WYalYh6Iip$QG4jvQ+UhkiInMUP/Lx+bwH6UK2iPARNB3qjAgw3HpQ=', NULL, 1, 'admin', 'System', 'Administrator', 'admin@antiquehub.com', 1, 1, '2026-10-20 04:48:06'),
  (2, 'pbkdf2_sha256$1500000$KTJA3tBUYO4PC6qOKqgjxw$+TvTnGBPB18YwqPGj8G5Elra0g0Al3kH1aoBjgTb9B0=', '2026-10-20 08:05:31', 0, 'sys_test_seller', '', '', 'sys_seller@antiquehub.test', 0, 1, '2026-10-20 08:04:51'),
  (3, 'pbkdf2_sha256$1500000$te9TL42GN8freriKJFZZpR$AZEbLkzVn7KosYnxScbT+h4usj6sDOZ2RTJuoeRA3Hk=', '2026-10-20 08:05:32', 0, 'sys_test_buyer', '', '', 'sys_buyer@antiquehub.test', 0, 1, '2026-10-20 08:04:52'),
  (4, 'pbkdf2_sha256$1500000$syd9fTRVReaAB27cNAlptj$vNaogB3whTftS00KV7QqNN9cCr/O7yrrW/FBLhFq7zI=', NULL, 0, 'perf_test_seller', '', '', 'perf_seller@antiquehub.test', 0, 1, '2026-10-20 08:07:03'),
  (5, 'pbkdf2_sha256$1500000$Wwo4NfeEJaMF233GKENjm0$kRzOA5Dvoy+Ylb8P/2Jek078upTkHvhomWbpkWf1K2M=', NULL, 0, 'chola_antiques', '', '', 'sales@cholaantiques.com', 0, 1, '2026-10-20 08:14:38'),
  (6, 'pbkdf2_sha256$1500000$JzTjU3jlhn4Gq256BSTD2Z$7R/peQMCA97ptU3V1/kCGGHdHM8dnurisNUwX/vt6Bo=', NULL, 0, 'deccan_relics', '', '', 'info@deccanrelics.com', 0, 1, '2026-10-20 08:14:39'),
  (7, 'pbkdf2_sha256$1500000$YHi9TH0tw5zu3ixILgfINa$HmIDU/LkEwzFuLAlwlnprps5zdj45XWmpF8Gzo75Uf4=', NULL, 0, 'rajputana_heritage', '', '', 'curios@rajputana.com', 0, 1, '2026-10-20 08:14:40'),
  (8, 'pbkdf2_sha256$1500000$H93bxNpsJcTYT5vEIrVgvj$F4Ex3wpqK/IRk2q6yBXcmVEGZDSq1Hk5kEaYvLS4eoQ=', NULL, 0, 'malabar_treasures', '', '', 'contact@malabartreasures.com', 0, 1, '2026-10-20 08:14:40'),
  (9, 'pbkdf2_sha256$1500000$7w8R1NelIxiLkeNz9gEG8K$+jXH7mMNL7trbI54LcrCgmV0pdNQ47cEJpBYUVtzvXg=', NULL, 0, 'collector_roy', '', '', 'roy.vintage@curators.in', 0, 1, '2026-10-20 08:14:41'),
  (10, 'pbkdf2_sha256$1500000$UtklLXNIeejDdE1Xtu4A0W$qksOJHCEgxqpRCIvv/9TWA8D54tvNV5KSh08Ysc6Yqg=', NULL, 0, 'priya_curator', '', '', 'priya.curator@heritage.org', 0, 1, '2026-10-20 08:14:42');

-- ------------------------------------------------------------
-- Data for table `role` (3 rows)
-- ------------------------------------------------------------
INSERT INTO `role` (`roleid`, `role`) VALUES
  (1, 'Admin'),
  (2, 'Seller'),
  (3, 'Buyer');

-- ------------------------------------------------------------
-- Data for table `state` (6 rows)
-- ------------------------------------------------------------
INSERT INTO `state` (`stateid`, `state`) VALUES
  (1, 'Kerala'),
  (2, 'Rajasthan'),
  (3, 'Tamil Nadu'),
  (4, 'Karnataka'),
  (5, 'West Bengal'),
  (6, 'Maharashtra');

-- ------------------------------------------------------------
-- Data for table `district` (14 rows)
-- ------------------------------------------------------------
INSERT INTO `district` (`distid`, `dist`, `state_id`) VALUES
  (1, 'Ernakulam', 1),
  (2, 'Thiruvananthapuram', 1),
  (3, 'Jaipur', 2),
  (4, 'Udaipur', 2),
  (5, 'Chennai', 3),
  (6, 'Madurai', 3),
  (7, 'Thanjavur', 3),
  (8, 'Thrissur', 1),
  (9, 'Mysuru', 4),
  (10, 'Bengaluru', 4),
  (11, 'Ballari', 4),
  (12, 'Jodhpur', 2),
  (13, 'Kolkata', 5),
  (14, 'Mumbai', 6);

-- ------------------------------------------------------------
-- Data for table `location` (45 rows)
-- ------------------------------------------------------------
INSERT INTO `location` (`locid`, `locname`, `district_id`) VALUES
  (1, 'Fort Kochi Heritage Zone', 1),
  (2, 'Mattancherry Jew Town', 1),
  (3, 'Marine Drive Arts Enclave', 1),
  (4, 'Palayam Heritage Precinct', 2),
  (5, 'Kowdiar Palace Ward', 2),
  (6, 'Johari Bazaar Craft District', 3),
  (7, 'Hawa Mahal Quarter', 3),
  (8, 'Amer Heritage Corridor', 3),
  (9, 'City Palace Road', 4),
  (10, 'Lake Pichola Promenade', 4),
  (11, 'Mylapore Temple Ward', 5),
  (12, 'George Town Merchant Quarter', 5),
  (13, 'Meenakshi Temple Precinct', 6),
  (14, 'South Masi Street', 6),
  (15, 'Brihadisvara Belt', 7),
  (16, 'Kumbakonam Craft Zone', 7),
  (17, 'Palace Quarter', 7),
  (18, 'Meenakshi Temple Zone', 6),
  (19, 'South Gate Bazaar', 6),
  (20, 'Mylapore Heritage Precinct', 5),
  (21, 'George Town Antiques Market', 5),
  (22, 'Fort Kochi Jew Town', 1),
  (23, 'Mattancherry Palace Road', 1),
  (24, 'Vadakkumnathan Heritage Zone', 8),
  (25, 'Round South Artisans', 8),
  (26, 'East Fort Heritage Square', 2),
  (27, 'Kowdiar Royal Avenue', 2),
  (28, 'Palace Enclave', 9),
  (29, 'Sayyaji Rao Road Antiquities', 9),
  (30, 'Commercial Street Vintage Quarter', 10),
  (31, 'Malleshwaram Heritage', 10),
  (32, 'Hampi Ruins Heritage Zone', 11),
  (33, 'Johari Bazaar Gem Quarter', 3),
  (34, 'Amer Fort Crafts Precinct', 3),
  (35, 'Tripolia Bazaar', 3),
  (36, 'City Palace Quarter', 4),
  (37, 'Jagdish Temple Lane', 4),
  (38, 'Clock Tower Vintage Market', 12),
  (39, 'Mehrangarh Foothills', 12),
  (40, 'Park Street Heritage Suite', 13),
  (41, 'College Street Antiquities', 13),
  (42, 'Bowbazar Curios', 13),
  (43, 'Colaba Causeway Curios', 14),
  (44, 'Chor Bazaar Heritage Lane', 14),
  (45, 'Fort Arts District', 14);

-- ------------------------------------------------------------
-- Data for table `userprofile` (10 rows)
-- ------------------------------------------------------------
INSERT INTO `userprofile` (`userid`, `login_id`, `role_id`, `username`, `contactname`, `phone`, `email`, `address`, `state_id`, `district_id`, `location_id`, `regdate`, `status`) VALUES
  (1, 1, 1, 'admin', 'Director of Antiquities (Admin)', '9876543210', 'admin@antiquehub.com', 'National Antiquities Commission HQ', 3, 5, 20, '2026-10-20 04:48:07', 'Active'),
  (2, 2, 2, 'sys_test_seller', 'Imperial Chola Antiquities', '9876500001', 'sys_seller@antiquehub.test', '', 3, 7, 15, '2026-10-20 08:04:52', 'Active'),
  (3, 3, 3, 'sys_test_buyer', 'Maharaja Heritage Collection', '9876500002', 'sys_buyer@antiquehub.test', '', 3, 7, 15, '2026-10-20 08:04:52', 'Active'),
  (4, 4, 2, 'perf_test_seller', 'Performance Benchmark Seller', '9900000000', 'perf_seller@antiquehub.test', '', NULL, NULL, NULL, '2026-10-20 08:07:04', 'Active'),
  (5, 5, 2, 'chola_antiques', 'Thanjavur Royal Antiques Co.', '9876501101', 'sales@cholaantiques.com', '14 Brihadisvara South Street', 3, 7, 15, '2026-10-20 08:14:39', 'Active'),
  (6, 6, 2, 'deccan_relics', 'Deccan Heritage & Numismatics', '9876501102', 'info@deccanrelics.com', '28 Palace Enclave North', 4, 9, 28, '2026-10-20 08:14:40', 'Active'),
  (7, 7, 2, 'rajputana_heritage', 'Amer Imperial Armoury & Curios', '9876501103', 'curios@rajputana.com', '88 Johari Bazaar Gate', 2, 3, 33, '2026-10-20 08:14:40', 'Active'),
  (8, 8, 2, 'malabar_treasures', 'Malabar Spice Coast Antiquities', '9876501104', 'contact@malabartreasures.com', '10 Jew Town Synagogue Road', 1, 1, 22, '2026-10-20 08:14:41', 'Pending'),
  (9, 9, 3, 'collector_roy', 'Roy Vintage Collector', '9876502201', 'roy.vintage@curators.in', '44 Park Street Heritage Suite', 5, 13, 40, '2026-10-20 08:14:42', 'Active'),
  (10, 10, 3, 'priya_curator', 'Priya Art Historian', '9876502202', 'priya.curator@heritage.org', '102 Indiranagar 12th Main', 4, 10, 31, '2026-10-20 08:14:42', 'Active');

-- ------------------------------------------------------------
-- Data for table `category` (15 rows)
-- ------------------------------------------------------------
INSERT INTO `category` (`catid`, `category`, `description`) VALUES
  (1, 'Furniture', 'Vintage woodwork, colonial seating, and hand-carved heritage furniture.'),
  (2, 'Decor', 'Authentic period accents, wall decor, mirrors, and vintage sculptures.'),
  (3, 'Coins', 'Historical numismatics, ancient dynasties, and imperial currency.'),
  (4, 'Jewellery', 'Timeless adornments, temple jewellery, and antique handcrafted ornaments.'),
  (5, 'Artefacts', 'Archaeological relics, stone sculptures, manuscripts, and tribal art.'),
  (6, 'Collectibles', 'Mechanical oddities, vintage technology, nautical instruments, and rare ephemera.'),
  (7, 'Sacred Bronzes', ''),
  (8, 'Ancient Bronzes', ''),
  (9, 'Royal Weapons', ''),
  (10, 'Numismatics', ''),
  (11, 'Temple Antiquities', ''),
  (12, 'Coins & Numismatics', 'Ancient and medieval imperial coinage from Indian dynasties and the Silk Road.'),
  (13, 'Royal Armour & Weapons', 'Damascened steel weaponry, jewelled hilts, and ceremonial royal parade armaments.'),
  (14, 'Vintage Furniture & Decor', 'Colonial, regal palace, and teak/rosewood heritage cabinetry and furnishings.'),
  (15, 'Antiquarian Carpets & Textiles', 'Hand-knotted silk rugs, gold-thread brocades, and historic court shawls.');

-- ------------------------------------------------------------
-- Data for table `subcategory` (46 rows)
-- ------------------------------------------------------------
INSERT INTO `subcategory` (`subcatid`, `subcategory`, `category_id`) VALUES
  (1, 'Colonial Armchairs', 1),
  (2, 'Teak & Rosewood Writing Desks', 1),
  (3, 'Antique Almirahs & Wardrobes', 1),
  (4, 'Brass-Embossed Chests & Trunks', 1),
  (5, 'Vintage Wall Clocks & Pendulums', 2),
  (6, 'Handcrafted Brass & Bronze Statues', 2),
  (7, 'Traditional Persian & Kashmiri Rugs', 2),
  (8, 'Gilded Heritage Wall Mirrors', 2),
  (9, 'Ancient Mughal & Sultanate Mohurs', 3),
  (10, 'British East India Company Silver Rupees', 3),
  (11, 'Greco-Roman & Kushan Empire Coins', 3),
  (12, 'Princely States Minted Coins', 3),
  (13, 'Antique Kundan & Polki Necklaces', 4),
  (14, 'Heritage Temple Gold Bangles', 4),
  (15, 'Victorian Filigree Brooches', 4),
  (16, 'Traditional Navratna Rings', 4),
  (17, 'Indus Valley Pottery Replicas & Terracotta', 5),
  (18, 'Chola Dynasty Bronze Sculptures', 5),
  (19, 'Antique Palm Leaf Manuscripts', 5),
  (20, 'Tribal Dhokra Brass Sculptures', 5),
  (21, 'His Masters Voice (HMV) Gramophones', 6),
  (22, 'Vintage Brass Maritime Telescopes', 6),
  (23, '19th Century Mechanical Pocket Watches', 6),
  (24, 'Classic Folding Cameras', 6),
  (25, 'Chola Dynasty Idols', 7),
  (26, 'Ancient Bronzes Fine Artifacts', 8),
  (27, 'Royal Weapons Fine Artifacts', 9),
  (28, 'Numismatics Fine Artifacts', 10),
  (29, 'Temple Antiquities Fine Artifacts', 11),
  (30, 'Chola Dynasty', 12),
  (31, 'Mughal Empire', 12),
  (32, 'Pandyan Dynasty', 12),
  (33, 'British East India Company', 12),
  (34, 'Chola Bronzes', 7),
  (35, 'Hoysala Idols', 7),
  (36, 'Temple Deepams & Bells', 7),
  (37, 'Ritual Urulis', 7),
  (38, 'Mughal Damascene Daggers', 13),
  (39, 'Rajput Talwars & Pesh-Kabz', 13),
  (40, 'Ceremonial Shields', 13),
  (41, 'Dutch Colonial Teak Desks', 14),
  (42, 'Carved Rosewood Chests', 14),
  (43, 'Plantation Armchairs', 14),
  (44, 'Kashmiri Silk Carpets', 15),
  (45, 'Zardozi Embroidered Silks', 15),
  (46, 'Pashmina Heritage Shawls', 15);

-- ------------------------------------------------------------
-- Data for table `item` (10 rows)
-- ------------------------------------------------------------
INSERT INTO `item` (`itemid`, `item`, `title`, `category_id`, `subcategory_id`, `years_old`, `origin`, `post_date`, `description`, `img1`, `img2`, `price`, `status`, `seller_id`) VALUES
  (2004, 'CHOLA-NATARAJA-1050', '10th Century Chola Lost-Wax Bronze Shiva Nataraja', 7, 34, 980, 'Thanjavur Royal Foundry, Chola Empire', '2026-10-20 08:14:43', 'Magnificent lost-wax casting depicting Nataraja dancing within an aureole of cosmic fire (Prabha Mandala). Rich greenish-black authentic patina verified through spectroscopic analysis.', 'antiques/items/nataraja1_6GDeDGY.jpg', '', 240000.00, 'Available', 5),
  (2005, 'MUGHAL-DAGGER-1680', '17th Century Mughal Jade-Hilt Damascene Dagger (Khanjar)', 13, 38, 345, 'Delhi Imperial Armoury, Mughal Court', '2026-10-20 08:14:43', 'Curved double-edged wootz crucible steel blade with damascened gold koftgari inlay. The hilt is carved from pale mutton-fat nephrite jade terminating in a sculpted horse head.', 'antiques/items/mughal_dagger_khdnyyH.jpg', '', 165000.00, 'Available', 7),
  (2006, 'CHOLA-KAHAVANU-990', 'Raja Raja Chola I Gold Kahavanu Coin (10th C.)', 12, 30, 1030, 'Gangaikonda Cholapuram Mint', '2026-10-20 08:14:43', 'Exceptional grade uncirculated gold kahavanu showing king standing holding lotus on obverse, seated king holding conch on reverse. Weight: 4.3 grams. Certificate of authenticity included.', 'antiques/items/coin1_GMekz4J.jpg', '', 48000.00, 'Available', 6),
  (2007, 'PANDYAN-FISH-SILVER', '13th Century Pandyan Dynasty Silver Drachm (Twin Fish Emblem)', 12, 32, 750, 'Madurai Royal Mint', '2026-10-20 08:14:43', 'Rare Pandyan silver denomination depicting the sacred twin carp emblem flanked by royal parasol and flywhisks. Excellent strike and high relief.', 'antiques/items/pandyan_bIUiy9O.jpg', '', 18500.00, 'Available', 6),
  (2008, 'RAJPUT-TALWAR-1750', '18th Century Rajput Royal Court Talwar Sword', 13, 39, 275, 'Mewar Kingdom, Rajasthan', '2026-10-20 08:14:43', 'Traditional curved high-carbon steel blade with disc pommel hilt adorned with intricate floral gold damascening. Fitted in original velvet-covered wooden scabbard with pierced brass chape.', 'antiques/items/talwar1_9H9PLQQ.jpg', '', 89000.00, 'Available', 7),
  (2009, 'TEMPLE-DEEPAM-BRONZE', '19th Century Sacred Mayur Temple Oil Lamp (Deepam)', 7, 36, 160, 'Kumbakonam Temple Belt', '2026-10-20 08:14:43', 'Heavy solid cast bronze tiered ceremonial oil lamp surmounted by a gracefully sculpted peacock (Mayura). Five-wick oil reservoir with dark sacred temple patina.', 'antiques/items/lamp1_RDEEdE0.jpg', '', 32000.00, 'Available', 5),
  (2010, 'KERALA-URLI-BELLMETAL', 'Heritage Traditional Bell-Metal Cooking Uruli Vessel', 7, 37, 140, 'Mannar Bell Metal Artisans, Kerala', '2026-10-20 08:14:43', 'Masterfully cast heavy acoustic bell-metal uruli with dual cast loop handles. Resonates with deep chime when struck; ideal for heritage decor or floating water flowers.', 'antiques/items/urli_C4r2Fmi.jpg', '', 26000.00, 'Available', 5),
  (2011, 'COLONIAL-ROSEWOOD-BOX', '19th Century Anglo-Indian Brass-Inlaid Rosewood Treasure Box', 14, 42, 155, 'Malabar Coast Trading Post', '2026-10-20 08:14:43', 'Lustrous aged Malabar rosewood fitted with hand-chiseled pierced brass corners, strapwork hinges, and hidden compartment. Key included with original lock mechanism.', 'antiques/items/box1_uZnhFyd.jpg', '', 42000.00, 'Available', 6),
  (2012, 'KASHMIR-SILK-CARPET-1920', 'Vintage Hand-Knotted Kashmiri Pure Silk Hunting Carpet (Shikargah)', 15, 44, 105, 'Srinagar Weavers Guild, Kashmir', '2026-10-20 08:14:43', 'Superfine master weaver carpet featuring 650 knots per square inch. Shikargah hunting motif with natural vegetable dyes including madder, saffron, and indigo.', 'antiques/items/carpet1_knek9E0.jpg', '', 135000.00, 'Available', 7),
  (2013, 'COLONIAL-TEAK-PLANTER', '19th Century British East India Teakwood Planters Chair', 14, 43, 130, 'Nilgiri Tea Estates Bungalow', '2026-10-20 08:14:43', 'Authentic colonial plantation chair crafted from old-growth Burma teak with original hand-woven cane webbing and fold-out leg extensions.', 'antiques/items/chair_COWVqg8.jpg', '', 58000.00, 'Available', 5);

-- ------------------------------------------------------------
-- Data for table `stock` (10 rows)
-- ------------------------------------------------------------
INSERT INTO `stock` (`stockid`, `item_id`, `tot_arr_stock`, `cur_stock`, `stockdate`, `status`) VALUES
  (2004, 2004, 3, 3, '2026-10-20 08:16:27', 'In Stock'),
  (2005, 2005, 2, 2, '2026-10-20 08:16:27', 'In Stock'),
  (2006, 2006, 5, 5, '2026-10-20 08:16:27', 'In Stock'),
  (2007, 2007, 6, 6, '2026-10-20 08:16:27', 'In Stock'),
  (2008, 2008, 3, 3, '2026-10-20 08:16:27', 'In Stock'),
  (2009, 2009, 4, 4, '2026-10-20 08:16:27', 'In Stock'),
  (2010, 2010, 4, 4, '2026-10-20 08:16:27', 'In Stock'),
  (2011, 2011, 2, 2, '2026-10-20 08:16:27', 'In Stock'),
  (2012, 2012, 1, 1, '2026-10-20 08:16:27', 'In Stock'),
  (2013, 2013, 2, 2, '2026-10-20 08:16:27', 'In Stock');

-- ------------------------------------------------------------
-- Data for table `discount` (2 rows)
-- ------------------------------------------------------------
INSERT INTO `discount` (`discountid`, `applicable_cat_id`, `discount_percent`, `startdate`, `enddate`) VALUES
  (1, 12, 15.00, '2026-10-15', '2026-11-14'),
  (2, 7, 10.00, '2026-10-18', '2026-11-19');

-- ------------------------------------------------------------
-- Data for table `faq` (16 rows)
-- ------------------------------------------------------------
INSERT INTO `faq` (`faqid`, `faq`, `answer`) VALUES
  (1, 'How does Antique Hub verify the authenticity and historical provenance of listed relics?', 'Every antique artifact cataloged on Antique Hub undergoes a rigorous multi-tier provenance audit before being made available for acquisition. Sellers must be verified dealers approved by our heritage curation committee. Listing requirements mandate high-resolution hallmark proof images, estimated epoch documentation, archaeological origin, and strict compliance with the Antiquities and Art Treasures Act, 1972. Any artifact displaying signs of contemporary reproduction or questionable lineage is rejected immediately.'),
  (2, 'What qualifies an artifact as a genuine antique on Antique Hub?', 'In accordance with statutory heritage guidelines and museum conservation benchmarks, items on Antique Hub must generally be at least 100 years old to be classified as historical antiques. Rare vintage collectibles, numismatics, and mid-century art objects aged 50 to 99 years may be cataloged under designated vintage subcategories, provided their provenance, manufacturer hallmarks, and cultural significance are fully documented.'),
  (3, 'How are fragile antique artifacts packaged to prevent damage during transit?', 'We enforce specialized museum-grade packaging standards for all antique shipments. Each piece is cushioned using acid-free archival tissue, multi-layer high-density shock-absorbing foam, custom-molded interior supports, and reinforced double-walled corrugated or wooden crates. Fragile glass, terracotta, and bronze relics receive additional climate-barrier seals to withstand humidity and temperature fluctuations during national transport.'),
  (4, 'What are the estimated shipping timelines and how can I track my antique order?', 'Once an order is confirmed and undergoes pre-dispatch condition verification (within 24 to 48 business hours), it is dispatched via insured, white-glove logistics partners. Domestic deliveries across India typically arrive within 3 to 7 business days depending on destination geography. Buyers receive automated dispatch notifications and can monitor real-time shipping milestones directly on the ''Track Order Status'' page.'),
  (5, 'What is the return and refund policy if an antique arrives damaged or misdescribed?', 'Antique Hub provides a 48-hour Buyer Protection guarantee upon recorded delivery. Because antique relics are irreplaceable, buyers are advised to record a continuous unboxing video upon receipt. If an artifact arrives damaged in transit or displays material discrepancies from its cataloged description, buyers can initiate an inspection claim. Upon return and physical verification by our curation team, a 100% full refund is credited back to the original payment source.'),
  (6, 'What payment methods are supported and how is my financial data protected?', 'We accept all major Credit/Debit Cards (Visa, MasterCard, RuPay), Net Banking across 50+ Indian banks, Unified Payments Interface (UPI), and Cash on Delivery (COD) for eligible regional orders. All digital transactions are processed through PCI-DSS Level 1 compliant encrypted gateways with 256-bit SSL encryption. In strict compliance with RBI tokenization rules, raw card numbers and CVVs are never saved on our database servers.'),
  (7, 'How can an antique dealer or private collector become an approved seller?', 'Prospective sellers must register via our Seller Portal, providing their enterprise contact details, verifiable physical showroom address, state, district, and tax/ID documentation. All new seller profiles are initially assigned ''Pending'' status and cannot publish listings until our Administrator conducts a background verification and activates the account. Once activated, sellers gain full access to upload items, manage stock, and track sales.'),
  (8, 'What commissions are charged to sellers and when are sales proceeds disbursed?', 'Antique Hub operates on a transparent, flat commission model with zero hidden monthly subscription fees. Sellers receive complete visibility into item totals, applied promotional discounts, and net earnings via their Seller Hub dashboard. Following successful delivery of the artifact and completion of the 48-hour buyer verification window, sales proceeds are automatically disbursed directly into the seller''s registered bank account within 3 business days.'),
  (9, 'How does Antique Hub verify the authenticity and provenance of antique items?', 'Every listing on Antique Hub is subject to rigorous provenance screening. Sellers are required to upload high-resolution multi-angle photographs, hallmarks, microscopic patina examinations, and existing archaeological or family lineage certificates. Our curated inspection guidelines adhere to Indian Antiquities and Art Treasures Act norms.'),
  (10, 'What payment methods are supported on the platform?', 'Antique Hub supports major Credit Cards (Visa, MasterCard, RuPay, American Express) validated via the Modulo-10 Luhn algorithm, Debit Cards, Net Banking from leading scheduled banks, and Cash on Delivery (COD) for domestic buyers. All payment handling is strictly PCI-DSS compliant.'),
  (11, 'How are fragile and high-value antique artifacts shipped?', 'Items are packaged using museum-grade shock-absorbing foam, custom wooden archival crates, and climate-sealed packaging. Every shipment is fully insured up to the purchase valuation and transported via high-security tracked express couriers.'),
  (12, 'What is the return and refund policy for antique collectors?', 'Buyers have a 7-day inspection window upon delivery. If an item is demonstrated to diverge materially from the catalog description or fail metallurgical verification, a full refund is processed upon return of the item in its unaltered original state.'),
  (13, 'How do I become an approved Seller on Antique Hub?', 'Prospective sellers register through the portal with their business registration, government identification, and geographic location. Accounts remain in ''Pending'' status until our Administrator conducts background verification and activates the seller profile.'),
  (14, 'Can sellers purchase their own antique items?', 'No. Antique Hub enforces strict marketplace integrity rules. Buyers are prevented from adding or purchasing listings uploaded from their own seller accounts to stop wash-trading and artificial price inflation.'),
  (15, 'How are promotional discounts applied to antique orders?', 'Active promotional discounts are applied on a category-wide basis by the Administrator. The effective price is computed uniformly across the marketplace catalogue, product detail pages, shopping cart, and final checkout.'),
  (16, 'Is full credit card information stored on the server?', 'Never. Under PCI-DSS compliance regulations, Antique Hub never stores primary account numbers (PAN) or CVV codes. Only the last 4 digits, detected card network (e.g. Visa), issuing bank, and gateway transaction reference ID are retained.');

-- ------------------------------------------------------------
-- Data for table `purchase_master` (2 rows)
-- ------------------------------------------------------------
INSERT INTO `purchase_master` (`purchaseid`, `buyer_id`, `purdate`, `ship_charge`, `tot_amt`, `status`, `pay_status`) VALUES
  (2, 9, '2026-10-20 08:16:28', 0.00, 40800.00, 'Confirmed', 'Paid'),
  (3, 10, '2026-10-20 08:16:28', 250.00, 23650.00, 'Shipped', 'Paid');

-- ------------------------------------------------------------
-- Data for table `purchase` (2 rows)
-- ------------------------------------------------------------
INSERT INTO `purchase` (`pid`, `purchase_master_id`, `item_id`, `quantity`, `price`) VALUES
  (2, 2, 2006, 1, 40800.00),
  (3, 3, 2010, 1, 23400.00);

-- ------------------------------------------------------------
-- Data for table `payment` (2 rows)
-- ------------------------------------------------------------
INSERT INTO `payment` (`payid`, `buyer_id`, `purchase_master_id`, `amount`, `pay_date`, `method`, `status`, `card_last4`, `card_type`, `bank_name`, `transaction_ref`) VALUES
  (2, 9, 2, 40800.00, '2026-10-20 08:16:28', 'Credit Card', 'Success', '4242', 'Visa', 'HDFC Bank', 'TXN-AH-DEMO-20261020-001'),
  (3, 10, 3, 23650.00, '2026-10-20 08:16:28', 'Debit Card', 'Success', '1111', 'Visa', 'State Bank of India', 'TXN-AH-DEMO-20261020-002');

-- ------------------------------------------------------------
-- Data for table `comment` (2 rows)
-- ------------------------------------------------------------
INSERT INTO `comment` (`id`, `buyer_id`, `item_id`, `comments`, `rating`, `is_verified_buyer`, `is_flagged`, `cdate`, `updated_date`) VALUES
  (1, 9, 2006, 'Exceptional Raja Raja Chola gold kahavanu! The weight and patina are perfectly consistent with Thanjavur museum specimens. Shipped in tamper-proof archival casing with full documentation.', 5, 1, 0, '2026-10-20 08:16:28', '2026-10-20 08:16:28'),
  (2, 10, 2010, 'Magnificent acoustic bell metal uruli. Resonates cleanly and exhibits authentic 19th century hand-hammered surface marks. Very satisfied with the seller''s transparency.', 5, 1, 0, '2026-10-20 08:16:28', '2026-10-20 08:16:28');

-- ------------------------------------------------------------
-- Data for table `watchlisted` (2 rows)
-- ------------------------------------------------------------
INSERT INTO `watchlisted` (`listid`, `user_id`, `item_id`, `added_date`) VALUES
  (1, 9, 2004, '2026-10-20 08:16:28'),
  (2, 10, 2005, '2026-10-20 08:16:28');

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- End of Antique Hub MySQL Seed Dump
-- ============================================================================