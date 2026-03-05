# Combined Discord Bot

A unified Discord bot that combines multiple essential functionalities:

- **Order Command Generation** - Creates formatted commands for Fusion Assist, Fusion Order, Wool Order, and Pump Order with advanced card/email pool management
- **Channel Management** - Opens/closes channels with rate limiting and announcements
- **Webhook Order Tracking** - Automatically detects and caches order confirmations from delivery service webhooks
- **Advanced Debugging Tools** - Comprehensive debugging commands for troubleshooting webhook detection and embed parsing
- **Payment Management System** - Dynamic payment method toggles with interactive button displays
- **Multi-Pool Email System** - Separate email pools for different order types (main, pump_20off25, pump_25off)

## Features

### Order Commands (Owner Only)
- `/fusion_assist` - Generate Fusion assist commands with Postmates/UberEats modes
- `/fusion_order` - Generate Fusion order commands with email from pool
- `/wool_order` - Generate Wool order commands
- `/pump_order` - Generate Pump order commands with dedicated pump email pools
- `/reorder` - Generate reorder commands with email only (Fusion/Stewardess, no card required)
- `/finished` - Mark order as finished and move ticket to completed channel
- `/z` - Parse order information and display detailed breakdown with payment calculations
- `/vcc` - Pull a card from the pool and display in order format (quick card access)

- Automatic embed parsing from ticket bots
- Order webhook tracking - Use `/send_tracking` after a webhook posts to send tracking info to the ticket
- Card & Email pools with SQLite storage
- Multi-pool email system - Separate pools for different order types
- Comprehensive logging to JSON, CSV, and TXT files
- Custom card/email support - Use your own cards/emails without touching the pool
- Intelligent webhook caching - Automatically detects and caches order confirmations from multiple webhook formats
- VIP pricing support - Special pricing options for VIP customers
- Service fee override - Customize service fees per order

### Advanced Webhook Detection
- Automatic webhook processing - Detects tracking and checkout webhooks in real-time
- Multiple webhook formats supported:
  - Traditional field-based webhooks (Store, Name, Delivery Address)
  - Checkout webhooks (Account Email, Delivery Information, Items In Bag)
  - Description-based webhooks (like Stewardess format with embedded markdown)
- Smart name matching - Flexible matching system with multiple name variations for improved accuracy
- Timestamp-based caching - Only keeps the most recent webhook data for each order
- Comprehensive parsing - Extracts store, name, address, items, tracking URLs, and arrival times

### Channel Management
- `/open` - Slash command to rename channel to "open🟢🟢" and send announcements
- `/close` - Slash command to rename channel to "closed🔴🔴" and send closure notice
- `/break` - Slash command to put channel "on-hold🟡🟡"
- open message - Renames channel to "open🟢🟢" and sends announcements
- close/closed message - Renames channel to "closed🔴🔴" and sends closure notice
- Rate limiting - Maximum 2 renames per 10 minutes per Discord's limits
- Role pinging and embed announcements
- Silent mode - Use `/open mode:silent` to skip role ping announcements

### Admin Pool Management (Owner Only)
- `/add_card` - Add single card to pool with validation
- `/add_email` - Add single email to specific pool (main, pump_20off25, pump_25off) with priority option
- `/bulk_cards` - Upload text or CSV file with multiple cards (supports various CSV formats)
- `/bulk_emails_main` - Upload text file with emails for main pool
- `/bulk_emails_pump20` - Upload text file with emails for pump_20off25 pool
- `/bulk_emails_pump25` - Upload text file with emails for pump_25off pool
- `/read_cards` - View all cards in pool
- `/read_emails` - View emails in specific pool or all pools
- `/remove_card` - Remove specific card from pool
- `/remove_email` - Remove specific email from any pool
- `/remove_bulk_cards` - Remove multiple cards using text file
- `/remove_bulk_emails` - Remove multiple emails from any pool using text file
- Card validation - Luhn algorithm validation and CVV format checking

### Webhook & Order Tracking (Owner Only)
- `/send_tracking` - Send order tracking info for current ticket using cached webhook data
- `/scan_webhooks` - Manually scan channels for webhook order confirmations
- `/check_cache` - View current webhook cache contents
- `/debug_tracking` - Debug webhook lookup and ticket matching

### Advanced Debugging Tools (Owner Only)
- `/debug_embed_details` - Show detailed embed structure for debugging webhook detection
- `/simple_embed_debug` - Quick embed analysis without fetching specific messages
- `/raw_field_debug` - Show raw field names and values for troubleshooting
- `/check_specific_message` - Test detection logic on a specific message ID
- `/debug_stewardess_webhook` - Debug specific webhook formats that aren't being detected
- `/find_ticket` - Search for ticket embeds in channel
- `/test_webhook_parsing` - Test webhook parsing on recent messages
- `/debug_cache_timestamps` - Show cache entries with timestamps for debugging recency issues

### Logging & Analytics (Owner Only)
- `/print_logs` - View recent command logs with email and card tracking
- `/full_logs` - View recent command logs with complete email and command output
- `/log_stats` - View statistics for commands, emails, and cards used
- Automatic logging to multiple formats (JSON, CSV, TXT)
- Monthly log rotation with detailed tracking
- Card digit tracking - Logs digits 9-16 for security while maintaining traceability

### Additional Features
- `/payments` - Display payment methods with interactive buttons
- `/toggle_payment` - Enable/disable specific payment method buttons (Zelle, Venmo, PayPal, CashApp, Crypto)
- `/toggle_cashapp` - Legacy command for CashApp toggle (use `/toggle_payment` instead)
- `/wool_details` - Show parsed Wool order details for verification
- Dynamic payment buttons - Only show enabled payment methods
- Comprehensive error handling with user-friendly messages
- Smart field validation - Automatically handles N/A and empty fields
- Name normalization - Consistent formatting for commands and matching
- Invisible bot status - Bot appears offline for privacy

## Prerequisites
- Python 3.10 or higher
- pip for package management

## Installation
Clone or download the bot files:

```bash
mkdir combined-discord-bot
cd combined-discord-bot
```

Create a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration
**Environment variables:** Copy `.env.example` to `.env` and fill in your values:

```env
# Required
BOT_TOKEN=your_bot_token_here
OWNER_ID=123456789012345678

# Optional - comment out features you don't need
OPENER_CHANNEL_ID=1234567890123456789
ROLE_PING_ID=1352022044614590494
ORDER_CHANNEL_MENTION=<#1350935337269985334>
```

**Database initialization:** On first run, the bot will auto-create:
- `data/pool.db` for cards and emails
- `logs/` directory for command logging

## Running the Bot
```bash
python combinedbot.py
```

The bot will display which features are configured.

## Command Reference
See the Features section above for full command lists. Key commands:
- **Order:** `/fusion_assist`, `/fusion_order`, `/wool_order`, `/pump_order`, `/reorder`, `/z`, `/vcc`, `/finished`
- **Pool:** `/add_card`, `/add_email`, `/bulk_cards`, `/bulk_emails_main`, `/bulk_emails_pump20`, `/bulk_emails_pump25`, `/read_cards`, `/read_emails`, `/remove_card`, `/remove_email`, `/remove_bulk_cards`, `/remove_bulk_emails`
- **Channel:** `/open`, `/close`, `/break`
- **Webhook/Tracking:** `/send_tracking`, `/scan_webhooks`, `/check_cache`, `/debug_tracking`
- **Debug:** `/debug_embed_details`, `/simple_embed_debug`, `/raw_field_debug`, `/check_specific_message`, `/debug_stewardess_webhook`, `/find_ticket`, `/test_webhook_parsing`, `/debug_cache_timestamps`
- **Logs:** `/print_logs`, `/full_logs`, `/log_stats`
- **Utility:** `/payments`, `/toggle_payment`, `/wool_details`, `/z`

## File Structure
```
combined-discord-bot/
├── combinedbot.py
├── db.py
├── logging_utils.py
├── config.py
├── requirements.txt
├── .env.example
├── .env
├── README.md
├── bot/
│   ├── __init__.py
│   ├── views.py
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── channel.py
│   │   ├── order.py
│   │   └── vcc.py
│   └── utils/
│       ├── __init__.py
│       ├── card_validator.py
│       ├── channel_status.py
│       └── helpers.py
├── data/
│   └── pool.db
├── logs/
└── tests/
```

## Security Considerations
- All command responses are ephemeral (only visible to command user)
- Only the configured OWNER_ID can execute admin commands
- Bot runs in invisible status (appears offline) for privacy
- Card numbers and emails are logged - secure your log files appropriately
- Database files contain sensitive payment information - implement appropriate backups and security
