"""Combined Discord bot – order commands, channel management, pool admin, webhook tracking."""
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from pathlib import Path

from config import EXP_MONTH, EXP_YEAR, ZIP_CODE

try:
    from db import (
        get_and_remove_card as db_get_and_remove_card,
        get_and_remove_email as db_get_and_remove_email,
        get_pool_counts as db_get_pool_counts,
        close_connection,
        init_db,
    )
except ModuleNotFoundError:
    import importlib.util
    db_path = Path(__file__).resolve().parent / "db.py"
    spec = importlib.util.spec_from_file_location("db", db_path)
    db = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(db)
    db_get_and_remove_card = db.get_and_remove_card
    db_get_and_remove_email = db.get_and_remove_email
    db_get_pool_counts = db.get_pool_counts
    close_connection = db.close_connection
    init_db = db.init_db

try:
    from logging_utils import log_command_output, get_recent_logs, get_full_logs, get_log_stats
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from logging_utils import log_command_output, get_recent_logs, get_full_logs, get_log_stats

try:
    from bot.views import PaymentView, CopyablePaymentView
except ModuleNotFoundError:
    import importlib.util
    path = Path(__file__).resolve().parent / "bot" / "views.py"
    spec = importlib.util.spec_from_file_location("bot.views", path)
    views = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(views)
    PaymentView = views.PaymentView
    CopyablePaymentView = views.CopyablePaymentView

try:
    from bot.utils import channel_status, helpers, card_validator
except ModuleNotFoundError:
    import importlib.util
    base = Path(__file__).resolve().parent / "bot" / "utils"
    for name in ["channel_status", "helpers", "card_validator"]:
        spec = importlib.util.spec_from_file_location(f"bot.utils.{name}", base / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        globals()[name] = mod

try:
    from bot.commands import order as order_commands, admin as admin_commands
    from bot.commands import channel as channel_commands, vcc as vcc_commands
except ModuleNotFoundError:
    import importlib.util
    base = Path(__file__).resolve().parent / "bot" / "commands"
    order_commands = importlib.util.module_from_spec(
        importlib.util.spec_from_file_location("order", base / "order.py")
    )
    admin_commands = importlib.util.module_from_spec(
        importlib.util.spec_from_file_location("admin", base / "admin.py")
    )
    channel_commands = importlib.util.module_from_spec(
        importlib.util.spec_from_file_location("channel", base / "channel.py")
    )
    vcc_commands = importlib.util.module_from_spec(
        importlib.util.spec_from_file_location("vcc", base / "vcc.py")
    )
    for mod in (order_commands, admin_commands, channel_commands, vcc_commands):
        mod.loader.exec_module(mod)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID")) if os.getenv("OWNER_ID") else None
OPENER_CHANNEL_ID = int(os.getenv("OPENER_CHANNEL_ID")) if os.getenv("OPENER_CHANNEL_ID") else None
ROLE_PING_ID = os.getenv("ROLE_PING_ID", "1352022044614590494")
ORDER_CHANNEL_MENTION = os.getenv("ORDER_CHANNEL_MENTION", "<#1350935337269985334>")
DB_PATH = Path(os.getenv("DB_PATH", str(Path(__file__).parent / "data" / "pool.db")))


class CombinedBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.dm_messages = True
        super().__init__(command_prefix="!", intents=intents, status=discord.Status.invisible)
        self.init_database()

    def init_database(self):
        init_db()

    async def close(self):
        close_connection()
        await super().close()

    def get_and_remove_card(self):
        result = db_get_and_remove_card()
        if result is None:
            return None
        number, cvv = result
        pool_counts = db_get_pool_counts()
        card_count = pool_counts["cards"]
        return number, cvv, card_count == 0

    def get_and_remove_email(self, pool_type: str = "main", fallback_to_main: bool = False):
        return db_get_and_remove_email(pool_type, fallback_to_main=fallback_to_main)

    def get_pool_counts(self):
        return db_get_pool_counts()

    async def fetch_order_embed(self, channel, search_limit: int = 25):
        return await helpers.fetch_order_embed(channel, search_limit=search_limit)

    def parse_fields(self, embed):
        return helpers.parse_fields(embed)

    def normalize_name(self, name: str):
        return helpers.normalize_name(name)

    def format_name_csv(self, name: str):
        return helpers.format_name_csv(name)

    def is_valid_field(self, value: str):
        return helpers.is_valid_field(value)

    def owner_only(self, interaction):
        return helpers.owner_only(interaction)


def main():
    bot = CombinedBot()

    @bot.event
    async def on_ready():
        await bot.change_presence(status=discord.Status.invisible)
        print(f"Bot {bot.user} connected (invisible).")
        try:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} command(s).")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

    @bot.event
    async def on_message(message):
        if message.author.bot:
            return
        if OPENER_CHANNEL_ID and message.channel.id == OPENER_CHANNEL_ID:
            content = message.content.lower().strip()
            if content == "open":
                status = "open"
            elif content in ("close", "closed"):
                status = "close"
            elif content in ("break", "on hold", "hold"):
                status = "break"
            else:
                await bot.process_commands(message)
                return
            success, error = await channel_status.change_channel_status(message.channel, status)
            if success:
                await message.add_reaction("✅")
            else:
                await message.add_reaction("❌")
                await message.channel.send(f"{message.author.mention} {error}", delete_after=10)

        if message.webhook_id and message.embeds:
            for embed in message.embeds:
                field_names = {f.name for f in embed.fields}
                is_webhook, _ = helpers.detect_webhook_type(embed, field_names)
                if is_webhook:
                    try:
                        data = helpers.parse_webhook_fields(embed)
                        helpers.cache_webhook_data(
                            data, message_timestamp=message.created_at, message_id=message.id
                        )
                    except Exception as e:
                        print(f"Error parsing webhook: {e}")

        await bot.process_commands(message)

    channel_commands.setup(bot)
    order_commands.setup(bot)
    admin_commands.setup(bot)
    vcc_commands.setup(bot)

    return bot


if __name__ == "__main__":
    bot = main()
    if not BOT_TOKEN:
        print("Missing BOT_TOKEN in .env")
        exit(1)
    print("Starting combined Discord bot...")
    print(f"Opener channel: {OPENER_CHANNEL_ID or 'Not configured'}")
    print(f"Owner ID: {OWNER_ID or 'Not configured'}")
    try:
        import db
        counts = db.get_pool_counts()
        print(f"Pool status – Cards: {counts['cards']}; Emails: {counts['emails']}")
    except Exception as e:
        print(f"Pool status: {e}")
    bot.run(BOT_TOKEN)
