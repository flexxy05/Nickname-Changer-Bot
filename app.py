import discord
from discord.ext import commands
import json
import os
import hexlogger
import sys

class NicknameBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True
        
        super().__init__(command_prefix=".", intents=intents, help_command=None)
        self.guild_configs = {}
        self.config_path = "config.json"
        
    def load_guild_configs(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.guild_configs = data.get("guilds", {})
                    for g_cfg in self.guild_configs.values():
                        if "requests" not in g_cfg:
                            g_cfg["requests"] = {}
            else:
                self.guild_configs = {}
        except Exception as e:
            hexlogger.error(f"Error loading guild configurations: {e}")
            self.guild_configs = {}
            
    def save_config(self):
        try:
            token = "YOUR_BOT_TOKEN_HERE"
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        token = data.get("token", "YOUR_BOT_TOKEN_HERE")
                    except Exception:
                        pass
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump({"token": token, "guilds": self.guild_configs}, f, indent=4)
            hexlogger.success("Saved configuration successfully.")
        except Exception as e:
            hexlogger.error(f"Error saving config.json: {e}")

    def get_default_guild_config(self):
        return {
            "log_channel_id": None,
            "request_channel_id": None,
            "auto_approve": False,
            "sanitize_enabled": True,
            "strict_ascii": False,
            "block_leading_symbol": True,
            "auto_dehoist": True,
            "requests": {},
            "whitelist": []
        }

    async def setup_hook(self):
        self.load_guild_configs()
        await self.load_extension("cogs.event")
        await self.load_extension("cogs.nickname")
        from cogs.nickname import NicknameApprovalView
        self.add_view(NicknameApprovalView())
        hexlogger.success("Loaded persistent approval view successfully.")

    async def on_ready(self):
        hexlogger.info(f"Bot connected as: {self.user} (ID: {self.user.id})")
        try:
            hexlogger.info("Syncing application commands globally...")
            synced = await self.tree.sync()
            hexlogger.success(f"Successfully synced {len(synced)} application commands globally.")
        except Exception as e:
            hexlogger.error(f"Failed to sync application commands: {e}")

def main():
    token = os.environ.get("DISCORD_TOKEN")
    if not token and os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                config_token = data.get("token")
                if config_token and config_token != "YOUR_BOT_TOKEN_HERE":
                    token = config_token
        except Exception as e:
            hexlogger.error(f"Failed to read token from config.json: {e}")
            
    if not token:
        hexlogger.error("FATAL: Bot token not found! Add your token to config.json or set the DISCORD_TOKEN environment variable.")
        sys.exit(1)
        
    bot = NicknameBot()
    bot.run(token)

if __name__ == "__main__":
    main()
