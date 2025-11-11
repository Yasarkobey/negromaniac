import json
import asyncio
import discord
from mineflayer import Bot
from discord.ext import commands
from flask import Flask, request, render_template_string
import threading
import time
import os
from datetime import datetime

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

with open('commands.json', 'r') as f:
    commands_db = json.load(f)

# Load or create towny data
try:
    with open('towny_data.json', 'r') as f:
        towny_data = json.load(f)
except FileNotFoundError:
    towny_data = {
        "players": {},
        "towns": {},
        "nations": {},
        "sieges": {},
        "admin_logs": []
    }

# Save towny data function
def save_towny_data():
    with open('towny_data.json', 'w') as f:
        json.dump(towny_data, f, indent=2)

# Flask Web Panel
app = Flask(__name__)
web_running = False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🏙️ Towny Bot Admin Panel</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1e1e1e; color: white; }
        .container { max-width: 1200px; margin: 0 auto; }
        .panel { background: #2d2d2d; padding: 20px; margin: 10px 0; border-radius: 10px; }
        .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
        .stat-box { background: #3d3d3d; padding: 15px; border-radius: 5px; text-align: center; }
        .chat-box { width: 100%; height: 200px; background: #1a1a1a; color: white; border: 1px solid #444; padding: 10px; margin: 10px 0; }
        .input-group { display: flex; gap: 10px; margin: 10px 0; }
        input, textarea, select { 
            background: #3d3d3d; color: white; border: 1px solid #555; padding: 8px; border-radius: 5px; 
            flex: 1; 
        }
        button { 
            background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; 
        }
        button:hover { background: #45a049; }
        .tab { overflow: hidden; border: 1px solid #444; background: #2d2d2d; }
        .tab button { background: #3d3d3d; float: left; border: none; outline: none; cursor: pointer; padding: 14px 16px; }
        .tab button:hover { background: #4d4d4d; }
        .tab button.active { background: #4CAF50; }
        .tabcontent { display: none; padding: 20px; border: 1px solid #444; border-top: none; }
        .town-list, .nation-list { max-height: 400px; overflow-y: auto; }
        .town-item, .nation-item { background: #3d3d3d; margin: 5px 0; padding: 10px; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏙️ Towny Bot Admin Panel</h1>
        
        <div class="panel">
            <div class="stats">
                <div class="stat-box">
                    <h3>📊 Total Towns</h3>
                    <p>{{ towns_count }}</p>
                </div>
                <div class="stat-box">
                    <h3>👥 Total Players</h3>
                    <p>{{ players_count }}</p>
                </div>
                <div class="stat-box">
                    <h3>🏴 Total Nations</h3>
                    <p>{{ nations_count }}</p>
                </div>
            </div>
        </div>

        <div class="tab">
            <button class="tablinks" onclick="openTab(event, 'Chat')">💬 Human Chat</button>
            <button class="tablinks" onclick="openTab(event, 'Towns')">🏘️ Towns</button>
            <button class="tablinks" onclick="openTab(event, 'Nations')">🏴 Nations</button>
            <button class="tablinks" onclick="openTab(event, 'Sieges')">⚔️ Sieges</button>
            <button class="tablinks" onclick="openTab(event, 'Admin')">🔧 Admin</button>
        </div>

        <div id="Chat" class="tabcontent">
            <h3>💬 Human Chat Integration</h3>
            <div class="chat-box" id="chatMessages">
                {% for msg in chat_messages %}
                <div><strong>{{ msg.sender }}:</strong> {{ msg.message }} <em>({{ msg.time }})</em></div>
                {% endfor %}
            </div>
            <div class="input-group">
                <input type="text" id="chatInput" placeholder="Type your message here...">
                <button onclick="sendChat()">Send</button>
            </div>
            <div class="input-group">
                <select id="chatTarget">
                    <option value="global">🌍 Global Chat</option>
                    <option value="town">🏘️ Town Chat</option>
                    <option value="nation">🏴 Nation Chat</option>
                    <option value="admin">🔧 Admin Chat</option>
                </select>
                <input type="text" id="customTarget" placeholder="Specific town/nation (optional)">
            </div>
        </div>

        <div id="Towns" class="tabcontent">
            <h3>🏘️ Town Management</h3>
            <div class="input-group">
                <input type="text" id="searchTown" placeholder="Search towns..." onkeyup="searchTowns()">
                <button onclick="refreshTowns()">🔄 Refresh</button>
            </div>
            <div class="town-list" id="townList">
                {% for town in towns %}
                <div class="town-item">
                    <h4>{{ town.name }} (Mayor: {{ town.mayor }})</h4>
                    <p>💰 Balance: ${{ town.balance }} | 👥 Members: {{ town.residents_count }} | 📍 Claims: {{ town.claims }}</p>
                    <p>🏴 Nation: {{ town.nation or 'None' }} | 📅 Founded: {{ town.founded_date }}</p>
                    <button onclick="editTown('{{ town.name }}')">✏️ Edit</button>
                    <button onclick="viewTownMembers('{{ town.name }}')">👥 Members</button>
                </div>
                {% endfor %}
            </div>
        </div>

        <div id="Nations" class="tabcontent">
            <h3>🏴 Nation Management</h3>
            <div class="nation-list" id="nationList">
                {% for nation in nations %}
                <div class="nation-item">
                    <h4>{{ nation.name }} (King: {{ nation.king }})</h4>
                    <p>💰 Balance: ${{ nation.balance }} | 🏘️ Towns: {{ nation.towns_count }} | 👥 Capital: {{ nation.capital }}</p>
                    <p>🤝 Allies: {{ nation.allies }} | ⚔️ Enemies: {{ nation.enemies }}</p>
                    <button onclick="editNation('{{ nation.name }}')">✏️ Edit</button>
                </div>
                {% endfor %}
            </div>
        </div>

        <div id="Sieges" class="tabcontent">
            <h3>⚔️ SiegeWar Dashboard</h3>
            <div id="siegeList">
                {% for siege in sieges %}
                <div class="town-item">
                    <h4>⚔️ {{ siege.attacker }} vs {{ siege.defender }}</h4>
                    <p>⏰ Duration: {{ siege.duration }}h | 💰 War Chest: ${{ siege.war_chest }}</p>
                    <p>🎯 Banner Control: {{ siege.banner_control }} | 🏆 Status: {{ siege.status }}</p>
                </div>
                {% endfor %}
            </div>
        </div>

        <div id="Admin" class="tabcontent">
            <h3>🔧 Admin Commands</h3>
            <div class="input-group">
                <select id="adminCommand">
                    <option value="give_balance">💰 Give Balance</option>
                    <option value="set_balance">💳 Set Balance</option>
                    <option value="delete_town">🗑️ Delete Town</option>
                    <option value="set_mayor">👑 Set Mayor</option>
                    <option value="reload">🔄 Reload Plugin</option>
                </select>
                <input type="text" id="adminTarget" placeholder="Target (town/player)">
                <input type="text" id="adminValue" placeholder="Value/Amount">
                <button onclick="executeAdminCommand()">Execute</button>
            </div>
            <div class="chat-box">
                <h4>Admin Logs:</h4>
                {% for log in admin_logs %}
                <div>[{{ log.time }}] {{ log.action }} - {{ log.user }}</div>
                {% endfor %}
            </div>
        </div>
    </div>

    <script>
        function openTab(evt, tabName) {
            var i, tabcontent, tablinks;
            tabcontent = document.getElementsByClassName("tabcontent");
            for (i = 0; i < tabcontent.length; i++) {
                tabcontent[i].style.display = "none";
            }
            tablinks = document.getElementsByClassName("tablinks");
            for (i = 0; i < tablinks.length; i++) {
                tablinks[i].className = tablinks[i].className.replace(" active", "");
            }
            document.getElementById(tabName).style.display = "block";
            evt.currentTarget.className += " active";
        }

        function sendChat() {
            const message = document.getElementById('chatInput').value;
            const target = document.getElementById('chatTarget').value;
            const custom = document.getElementById('customTarget').value;
            
            if (message) {
                fetch('/send_chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: message, target: target, custom: custom})
                });
                document.getElementById('chatInput').value = '';
            }
        }

        function executeAdminCommand() {
            const command = document.getElementById('adminCommand').value;
            const target = document.getElementById('adminTarget').value;
            const value = document.getElementById('adminValue').value;
            
            fetch('/admin_command', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({command: command, target: target, value: value})
            });
        }

        function searchTowns() {
            // Implement town search
        }

        // Open default tab
        document.getElementsByClassName('tablinks')[0].click();
        
        // Auto-refresh every 30 seconds
        setInterval(() => { location.reload(); }, 30000);
    </script>
</body>
</html>
"""

class TownyManager:
    def __init__(self):
        self.chat_messages = []
        self.last_save = time.time()
    
    def add_chat_message(self, sender, message):
        self.chat_messages.append({
            "sender": sender,
            "message": message,
            "time": datetime.now().strftime("%H:%M:%S")
        })
        # Keep only last 50 messages
        if len(self.chat_messages) > 50:
            self.chat_messages.pop(0)
    
    def get_stats(self):
        return {
            "towns_count": len(towny_data.get("towns", {})),
            "players_count": len(towny_data.get("players", {})),
            "nations_count": len(towny_data.get("nations", {})),
            "towns": list(towny_data.get("towns", {}).values()),
            "nations": list(towny_data.get("nations", {}).values()),
            "sieges": list(towny_data.get("sieges", {}).values()),
            "chat_messages": self.chat_messages[-20:],  # Last 20 messages
            "admin_logs": towny_data.get("admin_logs", [])[-10:]  # Last 10 logs
        }

towny_manager = TownyManager()

@app.route('/')
def admin_panel():
    stats = towny_manager.get_stats()
    return render_template_string(HTML_TEMPLATE, **stats)

@app.route('/send_chat', methods=['POST'])
def send_chat():
    data = request.json
    towny_manager.add_chat_message("Admin", data['message'])
    
    # Send to Minecraft
    if mc_bot and mc_bot.bot:
        chat_command = f"say [Admin] {data['message']}"
        mc_bot.bot.chat(chat_command)
    
    return {"status": "success"}

@app.route('/admin_command', methods=['POST'])
def admin_command():
    data = request.json
    command = data['command']
    target = data['target']
    value = data['value']
    
    # Log admin action
    towny_data["admin_logs"].append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": f"{command} on {target} with {value}",
        "user": "Web Panel"
    })
    save_towny_data()
    
    # Execute in Minecraft
    if mc_bot and mc_bot.bot:
        if command in commands_db["admin"]:
            cmd_template = commands_db["admin"][command]
            cmd = cmd_template.replace("{town}", target).replace("{amount}", value)
            mc_bot.bot.chat(f"/{cmd}")
    
    return {"status": "command_executed"}

def run_web_panel():
    app.run(host='0.0.0.0', port=config['web_panel']['port'])

# Minecraft Bot
class MinecraftBot:
    def __init__(self):
        self.bot = None
        self.connect_minecraft()
    
    def connect_minecraft(self):
        try:
            self.bot = Bot({
                'host': config['minecraft']['host'],
                'port': config['minecraft']['port'],
                'username': config['minecraft']['username'],
                'version': config['minecraft']['version']
            })
            
            self.setup_events()
            print("✅ Minecraft Towny Bot Connected!")
            
        except Exception as e:
            print(f"❌ Minecraft connection failed: {e}")
            # Retry after 30 seconds
            threading.Timer(30, self.connect_minecraft).start()
    
    def setup_events(self):
        @self.bot.on('message')
        def on_message(json_msg):
            message = json_msg.toString()
            print(f"📨 {message}")
            
            # Log chat messages
            if not message.startswith(config['prefix']):
                towny_manager.add_chat_message("Minecraft", message)
            
            # Handle commands
            if message.startswith(config['prefix']):
                self.handle_command(message)
        
        @self.bot.on('error')
        def on_error(error):
            print(f"❌ Minecraft Error: {error}")
        
        @self.bot.on('end')
        def on_end():
            print("🔌 Disconnected from Minecraft. Reconnecting...")
            threading.Timer(5, self.connect_minecraft).start()
    
    def handle_command(self, message):
        try:
            command = message[len(config['prefix']):].split()[0]
            args = message[len(config['prefix']):].split()[1:]
            
            # Find and execute command
            for category, cmds in commands_db.items():
                if command in cmds:
                    cmd_template = cmds[command]
                    # Simple argument replacement
                    for i, arg in enumerate(args):
                        cmd_template = cmd_template.replace(f"{{{'param'+str(i+1)}}}", arg)
                    
                    self.bot.chat(f"/{cmd_template}")
                    break
                    
        except Exception as e:
            print(f"❌ Command error: {e}")

# Discord Bot
class DiscordBot:
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(
            command_prefix=config['prefix'],
            intents=intents,
            help_command=None
        )
        self.setup_commands()
    
    def setup_commands(self):
        @self.bot.event
        async def on_ready():
            print(f'✅ Discord Bot Ready: {self.bot.user}')
            await self.bot.change_presence(activity=discord.Game(name="Towny | !help"))
        
        @self.bot.command(name='help')
        async def help_command(ctx):
            """Show all available commands"""
            embed = discord.Embed(
                title="🏙️ Towny Bot Commands",
                description="**Prefix:** `!`\n\n**Categories:**",
                color=0x00ff00
            )
            
            for category, cmds in commands_db.items():
                cmd_list = "\n".join([f"`{cmd}`" for cmd in cmds.keys()])
                embed.add_field(
                    name=f"**{category.upper()}**",
                    value=cmd_list,
                    inline=True
                )
            
            embed.set_footer(text="Use !<command> to execute. Admin panel: /admin")
            await ctx.send(embed=embed)
        
        @self.bot.command(name='town')
        async def town_info(ctx, town_name=None):
            """Get town information"""
            if not town_name:
                await ctx.send("❌ Please specify a town name: `!town <town_name>`")
                return
            
            # Get town data or simulate
            embed = discord.Embed(
                title=f"🏘️ Town: {town_name}",
                color=0x3498db
            )
            
            embed.add_field(name="Mayor", value="Player1", inline=True)
            embed.add_field(name="Balance", value="$1,000", inline=True)
            embed.add_field(name="Members", value="5", inline=True)
            embed.add_field(name="Nation", value="None", inline=True)
            embed.add_field(name="Claims", value="10", inline=True)
            embed.add_field(name="Founded", value="2024-01-01", inline=True)
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='nation')
        async def nation_info(ctx, nation_name=None):
            """Get nation information"""
            if not nation_name:
                await ctx.send("❌ Please specify a nation name: `!nation <nation_name>`")
                return
            
            embed = discord.Embed(
                title=f"🏴 Nation: {nation_name}",
                color=0xe74c3c
            )
            
            embed.add_field(name="King", value="Player2", inline=True)
            embed.add_field(name="Balance", value="$5,000", inline=True)
            embed.add_field(name="Towns", value="3", inline=True)
            embed.add_field(name="Capital", value="CapitalTown", inline=True)
            embed.add_field(name="Allies", value="2", inline=True)
            embed.add_field(name="Enemies", value="1", inline=True)
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='siege')
        async def siege_info(ctx, town_name=None):
            """Get siege information"""
            if not town_name:
                await ctx.send("❌ Please specify a town: `!siege <town_name>`")
                return
            
            embed = discord.Embed(
                title=f"⚔️ Siege: {town_name}",
                color=0xf39c12
            )
            
            embed.add_field(name="Attacker", value="AttackerNation", inline=True)
            embed.add_field(name="Defender", value="DefenderTown", inline=True)
            embed.add_field(name="Duration", value="24h", inline=True)
            embed.add_field(name="War Chest", value="$2,000", inline=True)
            embed.add_field(name="Banner Control", value="Attacker", inline=True)
            embed.add_field(name="Status", value="Ongoing", inline=True)
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='admin_panel')
        async def admin_panel_link(ctx):
            """Get admin panel link"""
            if not any(role.name in config['discord']['admin_roles'] for role in ctx.author.roles):
                await ctx.send("❌ You don't have permission to access the admin panel.")
                return
            
            embed = discord.Embed(
                title="🔧 Admin Panel",
                description=f"Access the admin panel here:\nhttp://your-repl-url.{config['web_panel']['port']}",
                color=0x9b59b6
            )
            embed.add_field(name="Password", value=f"`{config['web_panel']['password']}`", inline=True)
            embed.set_footer(text="Keep this information secure!")
            
            await ctx.author.send(embed=embed)  # DM the link
            await ctx.message.add_reaction('📨')

# Auto-save function
def auto_save():
    while True:
        time.sleep(config['towny']['auto_save'])
        save_towny_data()
        print("💾 Towny data auto-saved")

# Main execution
if __name__ == "__main__":
    print("🚀 Starting Minecraft Towny Bot...")
    
    # Start web panel in a separate thread
    web_thread = threading.Thread(target=run_web_panel, daemon=True)
    web_thread.start()
    print(f"🌐 Web panel started on port {config['web_panel']['port']}")
    
    # Start auto-save
    save_thread = threading.Thread(target=auto_save, daemon=True)
    save_thread.start()
    print("💾 Auto-save enabled")
    
    # Start Minecraft bot
    mc_bot = MinecraftBot()
    
    # Start Discord bot
    discord_bot = DiscordBot()
    
    # Run Discord bot
    try:
        discord_bot.bot.run(config['discord']['token'])
    except Exception as e:
        print(f"❌ Discord bot error: {e}")