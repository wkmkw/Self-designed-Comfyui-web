# websockets_api_example.py

# 该示例使用websockets API监听提示词执行完成事件，完成后通过/history端点下载图像

import websocket
import uuid
import json
import urllib.request
import urllib.parse
import os
import sys
from datetime import datetime  # 新增datetime导入

# 服务器地址配置
server_address = "127.0.0.1:8188"
client_id = str(uuid.uuid4())

def queue_prompt(prompt):
    """将提示词任务加入执行队列"""
    request_data = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(request_data).encode('utf-8')
    print("发送提示数据:", request_data)

    headers = {'Content-Type': 'application/json'}
    req = urllib.request.Request(
        f"http://{server_address}/prompt",
        data=data,
        headers=headers
    )
    
    try:
        response = urllib.request.urlopen(req)
        return json.loads(response.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP错误: {e.code} - {e.reason}")
        print(e.read().decode())
        raise

def get_image(filename, subfolder, folder_type):
    """根据文件名获取生成的图像数据"""
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(f"http://{server_address}/view?{url_values}") as response:
        return response.read()

def get_history(prompt_id):
    """获取指定提示ID的执行历史记录"""
    with urllib.request.urlopen(f"http://{server_address}/history/{prompt_id}") as response:
        return json.loads(response.read())

def get_images(ws, prompt, output_dir):
    """生成图像并返回实际保存的文件路径列表"""
    try:
        prompt_id = queue_prompt(prompt)['prompt_id']
        
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        break

        history = get_history(prompt_id)
        history = history[prompt_id]['outputs']
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"GUO_{timestamp}_{hash(prompt['6']['inputs']['text'][:10])}.PNG"
        filepath = os.path.join(output_dir, filename)
        
        for node_id in history:
            node_output = history[node_id]
            if 'images' in node_output:
                image = node_output['images'][0]
                image_data = get_image(image['filename'], image['subfolder'], image['type'])
                with open(filepath, "wb") as f:
                    f.write(image_data)
                return [filepath]
        
        return []

    except Exception as e:
        print(f"图像生成失败: {str(e)}")
        return []

def generate_image_with_comfyui(prompt_text, task_id):
    """使用新版工作流配置生成图像"""
    prompt = {
        "6": {
            "inputs": {
                "text": prompt_text,
                "speak_and_recognation": True,
                "clip": ["11", 0]
            },
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "CLIP文本编码器"}
        },
        "10": {
            "inputs": {"vae_name": "ae.sft"},
            "class_type": "VAELoader",
            "_meta": {"title": "VAE加载器"}
        },
        "11": {
            "inputs": {
                "clip_name1": "t5\\t5xxl_fp8_e4m3fn.safetensors",
                "clip_name2": "clip_l.safetensors",
                "type": "flux"
            },
            "class_type": "DualCLIPLoader",
            "_meta": {"title": "双CLIP加载器"}
        },
        "12": {
            "inputs": {
                "unet_name": "F.1基础算法模型-哩布在线可运行_F.1-dev-fp8.safetensors",
                "weight_dtype": "fp8_e4m3fn"
            },
            "class_type": "UNETLoader",
            "_meta": {"title": "UNET加载器"}
        },
        "13": {
            "inputs": {
                "noise": ["25", 0],
                "guider": ["22", 0],
                "sampler": ["16", 0],
                "sigmas": ["17", 0],
                "latent_image": ["70", 0]
            },
            "class_type": "SamplerCustomAdvanced",
            "_meta": {"title": "自定义采样器(高级)"}
        },
        "16": {
            "inputs": {"sampler_name": "euler"},
            "class_type": "KSamplerSelect",
            "_meta": {"title": "K采样器选择"}
        },
        "17": {
            "inputs": {
                "scheduler": "simple",
                "steps": 45,
                "denoise": 1,
                "model": ["73", 0]
            },
            "class_type": "BasicScheduler",
            "_meta": {"title": "基础调度器"}
        },
        "22": {
            "inputs": {
                "model": ["73", 0],
                "conditioning": ["6", 0]
            },
            "class_type": "BasicGuider",
            "_meta": {"title": "基础引导"}
        },
        "25": {
            "inputs": {"noise_seed": 1007042570686024},
            "class_type": "RandomNoise",
            "_meta": {"title": "随机噪波"}
        },
        "64": {
            "inputs": {
                "samples": ["13", 0],
                "vae": ["10", 0]
            },
            "class_type": "VAEDecode",
            "_meta": {"title": "VAE解码"}
        },
        "65": {
            "inputs": {"images": ["64", 0]},
            "class_type": "PreviewImage",
            "_meta": {"title": "预览图像"}
        },
        "70": {
            "inputs": {
                "width": 512,
                "height": 512,
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage",
            "_meta": {"title": "空Latent"}
        },
        "73": {
            "inputs": {
                "lora_name": "F.1-矢量卡通风格LOGO_V1.safetensors",
                "strength_model": 2.5,
                "model": ["12", 0]
            },
            "class_type": "LoraLoaderModelOnly",
            "_meta": {"title": "LoRA加载器(仅模型)"}
        }
    }

    # 动态参数配置
    prompt["25"]["inputs"]["noise_seed"] = int(datetime.now().timestamp() * 1000) % 2**32
    prompt["17"]["inputs"]["steps"] = 30
    prompt["73"]["inputs"]["strength_model"] = 2.0

    output_directory = r"D:\comfyui-portable-nfc1.2-windows\ComfyUI\temp"
    ws = None
    
    try:
        ws = websocket.WebSocket()
        ws.connect(f"ws://{server_address}/ws?clientId={client_id}")
        
        generated_files = get_images(ws, prompt, output_directory)
        
        if not generated_files:
            print("未生成任何图像文件")
            return None

        latest_file = generated_files[0]
        
        if not os.path.exists(latest_file):
            print(f"文件不存在: {latest_file}")
            return None

        try:
            with open("latest_image.txt", "w") as f:
                f.write(latest_file)
            print(f"图像保存路径: {latest_file}")
            return latest_file
        except IOError as e:
            print(f"文件写入失败: {str(e)}")
            return None

    except websocket.WebSocketException as e:
        print(f"WebSocket连接错误: {str(e)}")
        return None
    finally:
        if ws and ws.connected:
            ws.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        prompt_text = sys.argv[1]
        generate_image_with_comfyui(prompt_text, "default_task")
    else:
        print("请提供提示词参数")