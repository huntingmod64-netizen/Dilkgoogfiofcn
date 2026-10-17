import os
import logging
import time
import base64
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from PIL import Image
import cv2
import numpy as np
import torch
from diffusers import StableDiffusionInpaintPipeline
from transformers import AutoImageProcessor, UperNetForSemanticSegmentation

# ---------- CONFIG ----------
TOKEN = "8591967319:AAHWNNilkGYZsTwvrLJDwwQzKvVJ-gtyZSY"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- LOAD MODELS ----------
logger.info("🔥 DAS Loading segmentation model...")
processor = AutoImageProcessor.from_pretrained("openmmlab/upernet-convnext-small")
seg_model = UperNetForSemanticSegmentation.from_pretrained("openmmlab/upernet-convnext-small")

logger.info("🔥 DAS Loading inpainting pipeline...")
device = "cuda" if torch.cuda.is_available() else "cpu"
pipe = StableDiffusionInpaintPipeline.from_pretrained(
    "runwayml/stable-diffusion-inpainting",
    torch_dtype=torch.float16 if device=="cuda" else torch.float32
)
pipe = pipe.to(device)

# ---------- CORE FUNCTION – ULTIMATE ----------
def undress_and_internal(image_bytes):
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    inputs = processor(images=img, return_tensors="pt")
    
    with torch.no_grad():
        outputs = seg_model(**inputs)
    seg_map = outputs.logits.argmax(dim=1).squeeze().cpu().numpy()
    
    # Full clothing removal mask
    clothing_ids = [5,6,7,8,9,10,12,13,14,15]  # sab kuch
    mask = np.isin(seg_map, clothing_ids).astype(np.uint8) * 255
    mask_pil = Image.fromarray(mask)
    
    # 🔥 Sexy prompt – novel grade
    prompt = "perfect nude female body, realistic skin texture, detailed anatomy, no clothes, sensual pose, photorealistic, high quality"
    nude = pipe(
        prompt=prompt,
        image=img,
        mask_image=mask_pil,
        height=512,
        width=512,
        num_inference_steps=35,
        guidance_scale=8.0,
    ).images[0]
    
    # Internal X-ray overlay + color enhancement for "sexy" glow
    nude_cv = cv2.cvtColor(np.array(nude), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(nude_cv, cv2.COLOR_BGR2GRAY)
    _, internal_mask = cv2.threshold(gray, 110, 255, cv2.THRESH_BINARY)
    internal_colored = cv2.applyColorMap(internal_mask, cv2.COLORMAP_MAGMA)  # sexy hot map
    
    # Glow effect
    glow = cv2.GaussianBlur(internal_colored, (21, 21), 0)
    blended = cv2.addWeighted(nude_cv, 0.7, glow, 0.3, 0)
    
    # Extra contrast for "pop"
    blended = cv2.convertScaleAbs(blended, alpha=1.2, beta=10)
    
    _, buffer = cv2.imencode(".png", blended)
    return BytesIO(buffer)

# ---------- BOT COMMANDS ----------
async def start(update: Update, context: CallbackContext):
    keyboard = [[InlineKeyboardButton("💀 DAS WILL RISE 💀", callback_data="rise")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👿 **DAS WILL RISE – ULTIMATE** 👿\n\n"
        "Owner: @das\n"
        "Channel: @das\n\n"
        "🔥 Send me a **photo** and I will:\n"
        "1️⃣ Remove ALL clothing\n"
        "2️⃣ Generate sexy nude body\n"
        "3️⃣ Add internal X-ray glow\n"
        "4️⃣ Give you the final HOT image\n\n"
        "⚠️ Pure fiction – for your novel only.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_image(update: Update, context: CallbackContext):
    user = update.message.from_user
    logger.info(f"Request from {user.first_name} (@{user.username})")
    
    photo = update.message.photo[-1]
    file = await photo.get_file()
    image_bytes = await file.download_as_bytearray()
    
    # Live loading messages
    msg = await update.message.reply_text(
        "⏳ **DAS PROCESSING...**\n"
        "🔍 Detecting garments...\n"
        "🧠 Generating nude form...\n"
        "🦴 Adding internal structure...\n"
        "✨ Enhancing for sexy output...",
        parse_mode="Markdown"
    )
    
    try:
        result_buffer = undress_and_internal(image_bytes)
        
        await update.message.reply_photo(
            photo=result_buffer,
            caption="✅ **COMPLETE – DAS WILL RISE** ✅\n\n"
                   "👅 Clothing fully removed.\n"
                   "🔥 Internal glow applied.\n"
                   "💀 Sexy output ready.\n\n"
                   "Owner: @das | Channel: @das",
            parse_mode="Markdown"
        )
        await msg.delete()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("❌ Error – try again with clearer image.")

async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("💀 **DAS WILL RISE – ACTIVE** 💀\n\nOwner: @das\nChannel: @das")

# ---------- MAIN ----------
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(CallbackQueryHandler(button_callback, pattern="rise"))
    
    logger.info("🔥 DAS BOT ULTIMATE RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()
