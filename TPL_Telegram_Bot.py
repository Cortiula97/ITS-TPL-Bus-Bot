import requests
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode  # Changed import here

# Telegram Bot Token
BOT_TOKEN = "8067108198:AAFs6KbjL_yBIoezq09p0w3UBdNpRbTAZcU"

# API Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

# In-memory storage for user preferences
user_preferences = {}

# Function to fetch bus data based on line and stop
def get_bus_data(linea, fermata):
    url = f"https://realtime.tplfvg.it/API/v1.0/polemonitor/mrcruns?StopCode={fermata}&IsUrban=true"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        bus_info_messages = []
        bus_locations = []

        for i, bus in enumerate(data):
            if bus["LineCode"] == linea:
                # Create a line info message with optional lines
                line_info_parts = [
                    f"<b>🚌 Linea {bus['LineCode']}</b>",
                    f"<i>📍 Direzione:</i> <u>{bus['Destination']}</u>",
                ]

                # Conditionally add optional fields
                if bus.get('ArrivalTime'):
                    line_info_parts.append(f"<b>🕒 Arrivo:</b> {bus['ArrivalTime']}")
                
                if bus.get('NextPasses'):
                    line_info_parts.append(f"<i>🔜 Prossimo passaggio:</i> {bus['NextPasses']}")
                
                if bus.get('Vehicle'):
                    line_info_parts.append(f"<b>🚍 Veicolo:</b> {bus['Vehicle']}")

                # Add separator only if it's not the last bus
                if i < len(data) - 1:
                    line_info_parts.append("━━━━━━━━━━━━━━━━━")

                # Join the parts
                line_info_html = "\n".join(line_info_parts)
                bus_info_messages.append(line_info_html)

                if bus.get("Latitude") and bus.get("Longitude"):
                    bus_locations.append({
                        "latitude": bus["Latitude"], 
                        "longitude": bus["Longitude"], 
                        "destination": bus["Destination"]
                    })

        # If no buses found, return a friendly message
        if not bus_info_messages:
            return "🚏 Nessun autobus disponibile per questa linea.", []

        # Join multiple bus infos with a newline
        full_bus_info = "\n".join(bus_info_messages)
        return full_bus_info, bus_locations

    except requests.exceptions.RequestException as e:
        return f"❌ Errore nel recupero dei dati: {e}", None

# Start command to show the menu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id not in user_preferences:
        user_preferences[user_id] = {"linea": "100", "fermata": "80904"}

    await show_menu(update)

# Function to show the main menu with buttons in the keyboard area
async def show_menu(update: Update):
    keyboard = [
        ["Visualizza Autobus 🚍"],
        ["Cambia Linea 🚏", "Cambia Fermata 🏁"],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Cosa vuoi fare?", reply_markup=reply_markup
    )

# Handle user messages for button interactions
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    preferences = user_preferences.get(user_id, {"linea": "100", "fermata": "80904"})

    if text == "Visualizza Autobus 🚍":
        linea = preferences["linea"]
        fermata = preferences["fermata"]
        bus_info, bus_locations = get_bus_data(linea, fermata)
        
        # Send the bus info with HTML parsing
        await update.message.reply_text(
            bus_info, 
            parse_mode=ParseMode.HTML
        )

        if bus_locations:
            for bus_location in bus_locations:
                # First send a text message with bus destination
                await update.message.reply_text(f"Posizione bus direzione {bus_location['destination']}")
                
                # Then send the location
                await context.bot.send_location(
                    chat_id=update.message.chat_id, 
                    latitude=bus_location["latitude"], 
                    longitude=bus_location["longitude"]
                )

    elif text == "Cambia Linea 🚏":
        await update.message.reply_text("Inserisci il numero della nuova linea:")
        context.user_data["awaiting_linea"] = True

    elif text == "Cambia Fermata 🏁":
        await update.message.reply_text("Inserisci il codice della nuova fermata:")
        context.user_data["awaiting_fermata"] = True

    elif context.user_data.get("awaiting_linea"):
        user_preferences[user_id]["linea"] = text
        context.user_data["awaiting_linea"] = False
        await update.message.reply_text(f"Linea impostata su {text}.")
        await show_menu(update)

    elif context.user_data.get("awaiting_fermata"):
        user_preferences[user_id]["fermata"] = text
        context.user_data["awaiting_fermata"] = False
        await update.message.reply_text(f"Fermata impostata su {text}.")
        await show_menu(update)

# Main function to start the bot
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    print("Bot Partito")
    application.run_polling()

if __name__ == "__main__":
    main()