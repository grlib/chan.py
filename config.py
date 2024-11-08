import yaml

# 打开YAML文件并读取内容
file = open('config.yaml', 'r')
config = yaml.safe_load(file)