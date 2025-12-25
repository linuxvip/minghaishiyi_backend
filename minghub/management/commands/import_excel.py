# pyright: reportAttributeAccessIssue=false
import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.conf import settings
from minghub.models import DestinyCase

class Command(BaseCommand):
    help = '导入Excel命例数据到数据库'

    def handle(self, *args, **kwargs):
        # Excel文件路径
        excel_path = os.path.join(settings.BASE_DIR, 'mingdata', '命海拾遗-命例库.xlsx')
        
        if not os.path.exists(excel_path):
            self.stdout.write(self.style.ERROR(f'Excel文件不存在: {excel_path}'))
            return

        try:
            # 使用pandas读取Excel文件
            self.stdout.write(self.style.SUCCESS(f'正在读取Excel文件: {excel_path}'))
            df = pd.read_excel(excel_path)
            
            # 清除现有数据
            DestinyCase.objects.all().delete()
            self.stdout.write(self.style.WARNING('已清除数据库中的现有命例数据'))
            
            # 导入数据到数据库
            imported_count = 0
            for index, row in df.iterrows():
                # 创建命例对象
                destiny_case = DestinyCase(
                    source=str(row.get('命例来源', ''))[:255],
                    gender=1 if str(row.get('性别', '')) == '乾造' else 0,
                    year_ganzhi=str(row.get('年柱', ''))[:10],
                    month_ganzhi=str(row.get('月柱', ''))[:10],
                    day_ganzhi=str(row.get('日柱', ''))[:10],
                    hour_ganzhi=str(row.get('时柱', ''))[:10],
                    feedback=str(row.get('命例反馈', '')),
                    original_url=str(row.get('原网页地址', ''))[:255] if row.get('原网页地址') else None,
                    label=str(row.get('命例标签', ''))[:255] if row.get('命例标签') else None
                )
                destiny_case.save()
                imported_count += 1
                
                # 每导入100条记录显示进度
                if imported_count % 100 == 0:
                    self.stdout.write(self.style.NOTICE(f'已导入 {imported_count} 条命例数据'))
            
            self.stdout.write(self.style.SUCCESS(f'数据导入完成！共导入 {imported_count} 条命例数据'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'导入数据时发生错误: {str(e)}'))