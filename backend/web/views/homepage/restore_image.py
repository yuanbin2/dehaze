import os
import uuid
import traceback
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser 

class RestoreImageView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request):
        # ==========================================
        # 调试大招：我们临时把模型初始化搬到里面来，
        # 只要报错，立刻把报错原因塞给前端！
        # ==========================================
        try:
            from web.views.homepage.util.image_recovery import UNetPredictor
            predictor = UNetPredictor()
        except Exception as e:
            # traceback.format_exc() 会把最详细的哪行代码错了都抓出来
            error_detail = traceback.format_exc()
            print("================ 崩溃详情 ================")
            print(error_detail)
            return Response({
                'result': f'模型崩溃了！原因：{str(e)}'
            })

        # 如果能活着走到这里，说明模型加载成功了！
        try:
            image_file = request.FILES.get('image')
            if not image_file:
                return Response({'result': '请上传需要恢复的图像文件'})

            unique_filename = f"restored_{uuid.uuid4().hex}.png"
            save_dir = os.path.join(settings.MEDIA_ROOT, 'restored_images')
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, unique_filename)

            result_path = predictor.process_and_save(image_file, save_path)

            if result_path:
                result_url = f"{settings.MEDIA_URL}restored_images/{unique_filename}"
                return Response({'result': 'success', 'image_url': result_url})
            else:
                return Response({'result': '图像处理失败'})

        except Exception as e:
            return Response({'result': f'系统异常: {str(e)}'})