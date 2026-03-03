import urllib.request
import re
import base64
import json
import os
from datetime import datetime, timezone, timedelta

# emoji到国家代码的映射
emoji_to_country = {
    '🇨🇳': 'CN', '🇺🇸': 'US', '🇸🇬': 'SG', '🇩🇪': 'DE', '🇬🇧': 'GB',
    '🇯🇵': 'JP', '🇰🇷': 'KR', '🇫🇷': 'FR', '🇷🇺': 'RU', '🇮🇳': 'IN',
    '🇧🇷': 'BR', '🇨🇦': 'CA', '🇦🇺': 'AU', '🇳🇱': 'NL', '🇮🇩': 'ID',
    '🇹🇭': 'TH', '🇻🇳': 'VN', '🇵🇭': 'PH', '🇲🇾': 'MY', '🇹🇼': 'TW',
    '🇭🇰': 'HK', '🇲🇴': 'MO', '🇨🇼': 'CW', '🇪🇸': 'ES', '🇹🇷': 'TR',
    '🇳🇴': 'NO', '🇺🇦': 'UA', '🇱🇻': 'LV', '🇰🇭': 'KH', '🇸🇪': 'SE',
    '🇫🇮': 'FI', '🇷🇴': 'RO', '🇧🇪': 'BE'
}

# 国家代码到中文名称的映射
country_code_to_name = {
    'CN': '中国', 'US': '美国', 'SG': '新加坡', 'DE': '德国', 'GB': '英国',
    'JP': '日本', 'KR': '韩国', 'FR': '法国', 'RU': '俄罗斯', 'IN': '印度',
    'BR': '巴西', 'CA': '加拿大', 'AU': '澳大利亚', 'NL': '荷兰', 'ID': '印度尼西亚',
    'TH': '泰国', 'VN': '越南', 'PH': '菲律宾', 'MY': '马来西亚', 'TW': '台湾',
    'HK': '香港', 'MO': '澳门', 'CW': '库拉索', 'ES': '西班牙', 'TR': '土耳其',
    'NO': '挪威', 'UA': '乌克兰', 'LV': '拉脱维亚', 'KH': '柬埔寨', 'SE': '瑞典',
    'FI': '芬兰', 'RO': '罗马尼亚', 'BE': '比利时', '未知': '未知'
}

class BsbbCrawler:
    def __init__(self):
        self.base_url = "https://www.bsbb.cc"
        self.node_file_url = f"{self.base_url}/V2RAY.txt"
        self.nodes = []

    def fetch_node_data(self):
        """获取节点数据"""
        try:
            # 添加用户代理头信息，模拟浏览器访问
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            req = urllib.request.Request(self.node_file_url, headers=headers)
            response = urllib.request.urlopen(req, timeout=10)
            data = response.read().decode('utf-8')
            return data.strip().split('\n')
        except Exception as e:
            print(f"获取节点数据时出错: {e}")
            return []

    def parse_node(self, node_line):
        """解析单个节点信息"""
        # 提取协议类型
        protocol_match = re.match(r'([^:]+)://', node_line)
        if not protocol_match:
            return None
            
        protocol = protocol_match.group(1).lower()
        
        # 提取备注信息（包含国家和延迟）
        remark_match = re.search(r'#(.+)$', node_line)
        remark = remark_match.group(1) if remark_match else ""
        
        # 提取国家代码和延迟
        # 从备注中提取国家代码（例如：🇺🇸 www.bsbb.cc vless-US 87ms）
        country_emoji_match = re.search(r'^([\U0001F1E6-\U0001F1FF]{2})', remark)
        country_code_match = re.search(r'([A-Z]{2})\s*www\.bsbb\.cc\s*[a-zA-Z]+-([A-Z]{2})', remark)
        latency_match = re.search(r'(\d+)ms$', remark)
        
        # 优先使用emoji中的国家代码，如果没有则使用原来的提取方式
        if country_emoji_match:
            country_emoji = country_emoji_match.group(1)
            country_code = emoji_to_country.get(country_emoji, "未知")
        elif country_code_match:
            country_code = country_code_match.group(2)
        else:
            country_code = "未知"
            
        latency = int(latency_match.group(1)) if latency_match else None
        
        # 提取主机和端口
        host, port = self.extract_host_port(node_line, protocol)
        
        return {
            "protocol": protocol,
            "country_code": country_code,
            "latency": latency,
            "host": host,
            "port": port,
            "raw": node_line
        }

    def extract_host_port(self, node_line, protocol):
        """从节点链接中提取主机和端口"""
        try:
            if protocol == "vmess":
                # Vmess节点需要base64解码
                encoded_data = node_line[8:]  # 去掉"vmess://"
                # 添加缺少的填充字符
                missing_padding = len(encoded_data) % 4
                if missing_padding:
                    encoded_data += '=' * (4 - missing_padding)
                
                # 处理非ASCII字符
                decoded_data = base64.b64decode(encoded_data.encode('ascii')).decode('utf-8')
                data = json.loads(decoded_data)
                host = data.get("add", "")
                port = data.get("port", "")
                return host, port
            else:
                # 其他协议类型
                if "?" in node_line:
                    url_part = node_line.split("?")[0]
                else:
                    url_part = node_line.split("#")[0]
                
                host_port = url_part.split("@")[-1].split(":")
                host = host_port[0] if len(host_port) > 0 else ""
                port = host_port[1] if len(host_port) > 1 else ""
                return host, port
        except Exception as e:
            # 不显示错误信息，避免干扰
            return "", ""

    def crawl(self):
        """执行爬取任务"""
        print("开始爬取 www.bsbb.cc 节点信息...")
        node_lines = self.fetch_node_data()
        
        if not node_lines:
            print("未能获取到节点数据")
            return
            
        for line in node_lines:
            if line.strip():
                node_info = self.parse_node(line.strip())
                if node_info:
                    self.nodes.append(node_info)
        
        print(f"爬取完成，共获取到 {len(self.nodes)} 个节点信息")
        print(f"总共处理了 {len(node_lines)} 行数据")
        return self.nodes

    def analyze_nodes(self):
        """分析节点信息"""
        if not self.nodes:
            print("没有节点数据可供分析")
            return
            
        # 统计总节点数
        total_nodes = len(self.nodes)
        
        # 统计去重后的节点数
        unique_nodes = len(set(node['raw'] for node in self.nodes))
        duplicate_nodes = total_nodes - unique_nodes
        
        # 按国家统计节点数
        country_count = {}
        for node in self.nodes:
            country = node['country_code']
            country_count[country] = country_count.get(country, 0) + 1
            
        # 按协议类型统计节点数
        protocol_count = {}
        for node in self.nodes:
            protocol = node['protocol']
            protocol_count[protocol] = protocol_count.get(protocol, 0) + 1
            
        # 打印统计信息
        print(f"\n节点统计信息:")
        print(f"总节点数: {total_nodes}")
        print(f"重复节点数: {duplicate_nodes}")
        print(f"去重后节点数: {unique_nodes}")
        
        print(f"\n按国家区域统计:")
        for country, count in sorted(country_count.items()):
            country_name = country_code_to_name.get(country, country)
            print(f"{country_name}: {count} 个节点")
            
        print(f"\n按协议类型统计:")
        for protocol, count in sorted(protocol_count.items()):
            print(f"{protocol}: {count} 个节点")
            
        return {
            'total': total_nodes,
            'unique': unique_nodes,
            'duplicates': duplicate_nodes,
            'countries': country_count,
            'protocols': protocol_count
        }

    def save_to_file(self, filename="nodes.txt"):
        """保存节点信息到文件（去重后）"""
        # 去重节点
        unique_nodes = list(set(node['raw'] for node in self.nodes))
        
        with open(filename, "w", encoding="utf-8") as f:
            for node_raw in unique_nodes:
                f.write(f"{node_raw}\n")
        print(f"去重后的节点信息已保存到 {filename}，共 {len(unique_nodes)} 个节点")

    def update_readme(self, analysis_result):
        """更新 README.md 文件"""
        readme_path = "../README.md"
        
        # 使用中国时区
        china_tz = timezone(timedelta(hours=8))
        now = datetime.now(china_tz)
        
        # 创建 README.md 内容
        readme_content = "# 爬虫结果统计\n\n"
        readme_content += f"最后更新时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        readme_content += f"总节点数: {analysis_result['total']}\n\n"
        readme_content += f"去重后节点数: {analysis_result['unique']}\n\n"
        readme_content += f"重复节点数: {analysis_result['duplicates']}\n\n"
        
        readme_content += "## 按国家区域统计\n\n"
        for country, count in sorted(analysis_result['countries'].items()):
            country_name = country_code_to_name.get(country, country)
            readme_content += f"- {country_name}: {count} 个节点\n"
        
        readme_content += "\n## 按协议类型统计\n\n"
        for protocol, count in sorted(analysis_result['protocols'].items()):
            readme_content += f"- {protocol}: {count} 个节点\n"
        
        # 写入 README.md 文件
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)
        
        print(f"README.md 已更新")

if __name__ == "__main__":
    crawler = BsbbCrawler()
    nodes = crawler.crawl()
    if nodes:
        # 分析节点信息
        analysis_result = crawler.analyze_nodes()
        # 保存去重后的节点信息
        crawler.save_to_file()
        # 更新 README.md
        crawler.update_readme(analysis_result)
