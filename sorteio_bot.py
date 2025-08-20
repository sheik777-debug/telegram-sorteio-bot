# sorteio_bot.py
# Bot de Sorteio no Telegram
# by ChatGPT (2025)

import os
import asyncio
import random
from dataclasses import dataclass, field
from typing import Dict, Set, Optional

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatMember,
    ChatMemberAdministrator,
    ChatMemberOwner,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.getenv("BOT_TOKEN")

@dataclass
class GiveawayState:
    active: bool = False
    winners_count: int = 1
    limit: int = 0
    message_text: str = "🎉 *SORTEIO ATIVO!* Clique em *Participar* para entrar."
    participants: Set[int] = field(default_factory=set)
    message_id: Optional[int] = None
    thread_id: Optional[int] = None

giveaways: Dict[int, GiveawayState] = {}

async def is_admin(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> bool:
    member: ChatMember = await context.bot.get_chat_member(chat_id, user_id)
    return isinstance(member, (ChatMemberAdministrator, ChatMemberOwner))

def ensure_state(chat_id: int) -> GiveawayState:
    if chat_id not in giveaways:
        giveaways[chat_id] = GiveawayState()
    return giveaways[chat_id]

def build_keyboard(state: GiveawayState) -> InlineKeyboardMarkup:
    join_btn = InlineKeyboardButton(text="🎟️ Participar", callback_data="join")
    status_btn = InlineKeyboardButton(text=f"👤 {len(state.participants)}", callback_data="noop")
    return InlineKeyboardMarkup([[join_btn, status_btn]])

# --- Commands ---
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "🤖 *Comandos do Sorteio*\n\n"
        "/sorteio - ativa o sorteio no grupo\n"
        "/msg_sorteio <texto> - altera a mensagem do sorteio\n"
        "/ganhadores <n> - define quantos ganhadores\n"
        "/limite <n> - limite de participantes (0 = sem limite)\n"
        "/status_sorteio - mostra o status atual\n"
        "/encerrar - encerra e sorteia os vencedores\n"
        "/cancelar_sorteio - cancela sem sortear\n",
        parse_mode=ParseMode.MARKDOWN,
    )

async def sorteio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    msg = update.effective_message
    if not await is_admin(context, chat.id, update.effective_user.id):
        return await msg.reply_text("⚠️ Apenas admins podem iniciar o sorteio.")
    state = ensure_state(chat.id)
    state.active = True
    if context.args:
        state.message_text = " ".join(context.args)
    state.participants.clear()
    keyboard = build_keyboard(state)
    sent = await msg.reply_text(
        state.message_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
    )
    state.message_id = sent.message_id
    await msg.reply_text("✅ Sorteio ativado. Use /ganhadores, /limite e /msg_sorteio para configurar.")

async def msg_sorteio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    msg = update.effective_message
    state = ensure_state(chat.id)
    if not await is_admin(context, chat.id, update.effective_user.id):
        return await msg.reply_text("⚠️ Apenas admins podem alterar a mensagem.")
    if not state.active:
        return await msg.reply_text("ℹ️ Nenhum sorteio ativo.")
    if not context.args:
        return await msg.reply_text("Use: /msg_sorteio <novo texto>")
    state.message_text = " ".join(context.args)
    await context.bot.edit_message_text(
        chat_id=chat.id,
        message_id=state.message_id,
        text=state.message_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=build_keyboard(state),
    )
    await msg.reply_text("✅ Mensagem do sorteio atualizada.")

async def ganhadores_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    msg = update.effective_message
    state = ensure_state(chat.id)
    if not await is_admin(context, chat.id, update.effective_user.id):
        return await msg.reply_text("⚠️ Apenas admins podem alterar.")
    if not context.args or not context.args[0].isdigit():
        return await msg.reply_text("Use: /ganhadores <número>")
    state.winners_count = int(context.args[0])
    await msg.reply_text(f"✅ Número de ganhadores definido para {state.winners_count}.")

async def limite_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    msg = update.effective_message
    state = ensure_state(chat.id)
    if not await is_admin(context, chat.id, update.effective_user.id):
        return await msg.reply_text("⚠️ Apenas admins podem alterar.")
    if not context.args or not context.args[0].isdigit():
        return await msg.reply_text("Use: /limite <número>")
    state.limit = int(context.args[0])
    await msg.reply_text(f"✅ Limite de participantes definido para {state.limit if state.limit>0 else 'ilimitado'}.")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = ensure_state(update.effective_chat.id)
    await update.effective_message.reply_text(
        f"📊 Status\nAtivo: {'Sim' if state.active else 'Não'}\n"
        f"Ganhadores: {state.winners_count}\n"
        f"Limite: {state.limit if state.limit>0 else 'ilimitado'}\n"
        f"Participantes: {len(state.participants)}",
        parse_mode=ParseMode.MARKDOWN,
    )

async def cancelar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    msg = update.effective_message
    state = ensure_state(chat.id)
    if not await is_admin(context, chat.id, update.effective_user.id):
        return await msg.reply_text("⚠️ Apenas admins podem cancelar.")
    state.active = False
    state.participants.clear()
    await msg.reply_text("🛑 Sorteio cancelado.")

async def encerrar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    msg = update.effective_message
    state = ensure_state(chat.id)
    if not await is_admin(context, chat.id, update.effective_user.id):
        return await msg.reply_text("⚠️ Apenas admins podem encerrar.")
    if not state.active:
        return await msg.reply_text("ℹ️ Nenhum sorteio ativo.")
    total = len(state.participants)
    if total == 0:
        return await msg.reply_text("😕 Ninguém participou.")
    winners_num = min(state.winners_count, total)
    winners_ids = random.sample(list(state.participants), winners_num)
    winners_mentions = [f"[usuário](tg://user?id={uid})" for uid in winners_ids]
    state.active = False
    await msg.reply_text(
        "🏁 Sorteio encerrado!\n\n" +
        "\n".join(f"{i+1}. {m}" for i, m in enumerate(winners_mentions)),
        parse_mode=ParseMode.MARKDOWN,
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    state = ensure_state(update.effective_chat.id)
    if query.data == "join" and state.active:
        if user.id in state.participants:
            await query.answer("Você já está participando.")
        else:
            if state.limit and len(state.participants) >= state.limit:
                await query.answer("⚠️ Limite atingido.", show_alert=True)
                return
            state.participants.add(user.id)
            await query.answer("Você entrou no sorteio! 🎟️")
            try:
                await query.edit_message_reply_markup(reply_markup=build_keyboard(state))
            except:
                pass

async def main():
    if not TOKEN:
        raise RuntimeError("Defina BOT_TOKEN no ambiente.")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("sorteio", sorteio_cmd))
    app.add_handler(CommandHandler("msg_sorteio", msg_sorteio_cmd))
    app.add_handler(CommandHandler("ganhadores", ganhadores_cmd))
    app.add_handler(CommandHandler("limite", limite_cmd))
    app.add_handler(CommandHandler("status_sorteio", status_cmd))
    app.add_handler(CommandHandler("cancelar_sorteio", cancelar_cmd))
    app.add_handler(CommandHandler("encerrar", encerrar_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Bot de sorteio iniciado.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
