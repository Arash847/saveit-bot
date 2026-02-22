import flet as ft
from telethon import TelegramClient, events, errors
import os
import asyncio

client = None
phone_number = ""

async def main(page: ft.Page):
    page.title = "SaveIt Bot - Downloader"
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 20

    title_text = ft.Text("SaveIt Telegram Bot", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200)
    subtitle_text = ft.Text("Self-Hosted Media Saver", size=12, color=ft.Colors.GREY_400)

    api_id_input = ft.TextField(label="API ID", hint_text="Example: 123456", width=300, text_size=14)
    api_hash_input = ft.TextField(label="API Hash", hint_text="Example: a1b2c3d4...", width=300, text_size=14, password=True, can_reveal_password=True)
    phone_input = ft.TextField(label="Phone Number", hint_text="+98912...", width=300, text_size=14)
    
    code_input = ft.TextField(label="Login Code", hint_text="12345", width=300, visible=False)
    password_input = ft.TextField(label="2FA Password (If enabled)", password=True, width=300, visible=False)

    logs_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    logs_container = ft.Container(
        content=logs_column,
        border=ft.border.all(1, ft.Colors.OUTLINE),
        border_radius=10,
        padding=10,
        width=400,
        height=300,
        bgcolor=ft.Colors.SURFACE_VARIANT,
        visible=False
    )

    action_button = ft.ElevatedButton(text="Connect & Start", width=300, height=45)
    logout_button = ft.IconButton(icon=ft.Icons.LOGOUT, visible=False, tooltip="Logout/Reset")

    def log(message, color=ft.Colors.WHITE):
        logs_column.controls.append(ft.Text(f"• {message}", color=color, size=12, font_family="Consolas"))
        page.update()
        logs_column.scroll_to(offset=-1, duration=300)

    async def save_media_handler(event):
        sender = await event.get_sender()
        me = await event.client.get_me()
        if sender.id != me.id: return
        
        status_msg = await event.reply("Downloading...")
        if not event.is_reply:
            await status_msg.edit("Please reply to a media.")
            return

        reply_msg = await event.get_reply_message()
        if not (reply_msg and reply_msg.media):
            await status_msg.edit("No media found.")
            return

        download_path = "downloads"
        os.makedirs(download_path, exist_ok=True)

        try:
            file_path = await event.client.download_media(reply_msg, file=download_path)
            await event.client.send_file("me", file_path, caption="Saved via App", force_document=True)
            await status_msg.edit("Saved successfully!")
            await event.delete()
            await asyncio.sleep(3)
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit(f"Error: {e}")

    async def start_bot_process(e):
        global client, phone_number
        if action_button.text == "Connect & Start":
            if not api_id_input.value or not api_hash_input.value or not phone_input.value:
                api_id_input.error_text = "Required" if not api_id_input.value else None
                page.update()
                return

            action_button.disabled = True
            action_button.text = "Connecting..."
            page.update()

            try:
                clean_phone = phone_input.value.replace("+", "").replace(" ", "")
                session_name = f"session_{clean_phone}"
                client = TelegramClient(session_name, int(api_id_input.value), api_hash_input.value)
                await client.connect()

                if not await client.is_user_authorized():
                    phone_number = phone_input.value
                    await client.send_code_request(phone_number)
                    api_id_input.visible = False
                    api_hash_input.visible = False
                    phone_input.visible = False
                    code_input.visible = True
                    action_button.text = "Verify Code"
                    action_button.disabled = False
                    page.update()
                else:
                    await on_login_success()
            except Exception as ex:
                action_button.disabled = False
                action_button.text = "Connect & Start"
                snack = ft.SnackBar(ft.Text(f"Error: {ex}"), bgcolor=ft.Colors.RED)
                page.overlay.append(snack)
                snack.open = True
                page.update()

        elif action_button.text == "Verify Code":
            if not code_input.value: return
            action_button.disabled = True
            page.update()
            try:
                await client.sign_in(phone_number, code_input.value)
                await on_login_success()
            except errors.SessionPasswordNeededError:
                code_input.visible = False
                password_input.visible = True
                action_button.text = "Verify Password"
                action_button.disabled = False
                page.update()
            except Exception as ex:
                action_button.disabled = False
                code_input.error_text = "Invalid Code"
                page.update()

        elif action_button.text == "Verify Password":
            try:
                await client.sign_in(password=password_input.value)
                await on_login_success()
            except Exception as ex:
                password_input.error_text = "Invalid Password"
                page.update()

    async def on_login_success():
        me = await client.get_me()
        api_id_input.visible = False
        api_hash_input.visible = False
        phone_input.visible = False
        code_input.visible = False
        password_input.visible = False
        action_button.visible = False
        logs_container.visible = True
        logout_button.visible = True
        title_text.value = f"Welcome, {me.first_name}!"
        subtitle_text.value = "Bot Active. Reply '.saveit'"
        subtitle_text.color = ft.Colors.GREEN
        client.add_event_handler(save_media_handler, events.NewMessage(pattern=r'\.saveit'))
        page.update()

    async def logout_click(e):
        if client: await client.disconnect()
        page.window.destroy()

    action_button.on_click = start_bot_process
    logout_button.on_click = logout_click

    page.add(
        ft.Column(
            [ft.Row([title_text, logout_button], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
             subtitle_text, ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
             api_id_input, api_hash_input, phone_input, code_input, password_input,
             ft.Divider(height=20, color=ft.Colors.TRANSPARENT), action_button, logs_container],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    )

ft.run(main)
