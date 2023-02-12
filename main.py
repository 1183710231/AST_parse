import os

import javalang
import javalang.tree as Tree
import os, pickle

class AST_parse():
    def get_father_var_name(self, path, var_dict, node):
        path_len = len(path) - 1
        if isinstance(path[path_len], list):
            path_len -= 1
        father_node = path[path_len]
        if hasattr(father_node,'qualifier') and (not father_node.qualifier is None):
            father_var_name = var_dict[father_node.qualifier] + '.' + father_node.member
        else:
            father_var_name = None
        return father_var_name

    def load_pkl(self, path):
        with open(path, 'rb') as f:
            data = pickle.load(f)
        return data
    def varname2pack(self, var_name, var_dict):


    def parse(self, dirname):
        # f_output = open()
        file_handle = open('1.txt', mode='w')
        file_handle.truncate(0)
        for maindir, subdir, file_name_list in os.walk(dirname):
            for java_file in file_name_list:
                if java_file.endswith('.java'):
                    apath = os.path.join(maindir, java_file)
                    f_input = open(apath, 'r', encoding='utf-8')
                    tree = javalang.parse.parse(f_input.read())
                    # pack_desc = dict()
                    pack_dict = self.load_pkl('api2desc.pkl')
                    # import_list = dict()
                    var_dict = dict()
                    api_list = list()
                    class_pack_dict = dict()
                    for path, node in tree:
                        # print(path, node)
                        # 提取导入类，并获得包信息
                        if isinstance(node,Tree.Import):
                            # import_list.append(node.path)
                            pakage_list = node.path.split('.')
                            class_name = pakage_list[len(pakage_list)-1]
                            pack_name = pakage_list[0]


                        #通过path获得局部变量定义，未确定类
                        if isinstance(node, Tree.VariableDeclarator):
                            path_len = len(path) - 1
                            if isinstance(path[path_len], list):
                                path_len -= 1
                            # var_dict[node.name] = path[path_len].type.name
                            var_class_name = path[path_len].type.name
                            if class_pack_dict.__contains__(var_class_name):
                                var_dict[node.name] = class_pack_dict.get(var_class_name)
                        # 形参，获取变量名及类
                        if isinstance(node, Tree.FormalParameter):
                            # var_dict[node.name] = node.type.name
                            par_class_name = node.type.name
                            if class_pack_dict.__contains__(par_class_name):
                                var_dict[node.name] = class_pack_dict.get(par_class_name)
                        # 方法调用，须与变量名关联，变量名与类关联，类与包信息关联
                        if isinstance(node, Tree.MethodInvocation) and (var_dict.__contains__(node.qualifier)):
                            var_name = node.qualifier
                            # 多级调用，
                            if not var_name:
                                var_name = self.get_father_var_name(path, var_dict, node)
                                if (not var_name is None) :
                                    # 为应对重载方法，此处需通过参数来判断方法返回值，并利用返回值
                                    attrs_list = list()
                                    for attr in node.arguments:
                                        attrs_list.append(attr.member)
                                    api_list.append(var_dict.get(var_name) + '.' + node.member)
                            else:
                                method_type = var_dict[var_name]
                                api_list.append(method_type + '.' + node.member)
                        file_handle.write('path=' + str(path) + '\n')
                        file_handle.write('node=' + str(node) + '\n'+ '\n'+ '\n')
        # print(import_list)
        print(var_dict)
        print(api_list)
        file_handle.close()




if __name__ == '__main__':
    my_parse = AST_parse()
    # my_parse.parse('clicy-master')
    my_parse.parse('demo_test')



