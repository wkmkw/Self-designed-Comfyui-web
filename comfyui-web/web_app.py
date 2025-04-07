# web_app.py

from flask import Flask, render_template, request, jsonify, send_file  # Ensure 'request' is imported
import subprocess  # 用于运行外部脚本
import os          # 文件路径操作
import uuid
app = Flask(__name__)  # 创建Flask应用实例

@app.route('/generate_image', methods=['POST'])
def generate_image():
    """处理图像生成请求"""
    try:
        # 从JSON请求体中获取提示词，默认为"default"
        prompt_text = request.json.get("prompt_text", "default")
        
        print(f"开始生成图像，提示词: {prompt_text}")  # 添加日志
        
        # 检查目标脚本是否存在
        script_path = 'C:/Users/19519362920/Desktop/comfyui-web/websockets_api_example.py'
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"生成脚本未找到: {script_path}")
        
        # 调用外部Python脚本进行图像生成
        result = subprocess.run(
            ['python', script_path, prompt_text],
            check=True,
            capture_output=True,
            text=True
        )
        
        print(f"脚本输出: {result.stdout}")  # 添加日志
        
        # 返回成功响应
        return jsonify({
            "status": "success",
            "message": "图像生成已启动",
            "output": result.stdout,
            "prompt": prompt_text  # 添加提示词到响应中
        })
    
    except subprocess.CalledProcessError as e:
        # 处理子进程错误
        error_message = e.stderr or str(e)
        print("子进程错误:", error_message)
        return jsonify({
            "status": "error",
            "message": "图像生成失败",
            "error": error_message
        }), 500  # 返回500错误状态码

    except Exception as e:
        # 处理其他未知错误
        print("未知错误:", str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/get_latest_image', methods=['GET'])
def get_latest_image():
    """获取最新生成的图像"""
    try:
        # 从状态文件读取最新图像路径
        with open("latest_image.txt", "r") as f:
            image_path = f.read().strip()
        
        if os.path.exists(image_path):
            # 发送图像文件
            return send_file(image_path, mimetype='image/png')
        else:
            return jsonify({"status": "error", "message": "图像未找到"}), 404
    except FileNotFoundError:
        return jsonify({"status": "error", "message": "尚未生成图像"}), 404

@app.route('/')  # 原路由保持不变，保持logozhizuo.html功能
def generate_page():
    """原有的logo生成页面（路由保持根路径/）"""
    return render_template('logozhizuo.html')

# 新增主页路由
@app.route('/index')  # 新增路径/index
def index():
    """主页面"""
    return render_template('index.html')

# 新增关于页面路由
@app.route('/about')  # 新增路径/about
def about():
    """关于页面"""
    return render_template('about.html')

if __name__ == "__main__":
    app.run(port=5001)
