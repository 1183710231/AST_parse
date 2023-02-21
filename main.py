import os

import javalang
import javalang.tree as Tree
import os, pickle
import operator

class TypeExceptin(Exception):
    "this is user's Exception for check the length of name "
    def __init__(self,str):
        self.str = str
    def __str__(self):
        print("该情况暂未处理:"+self.str)

class AST_parse():
    def get_father_return_class(self, path, var_dict, node):
        path_len = len(path) - 1
        if isinstance(path[path_len], list):
            path_len -= 1
        father_node = path[path_len]
        # undo 如果是两层掉用，则拿到第二层的变量
        if hasattr(father_node, 'qualifier') and (not father_node.qualifier is None):
            father_var_name = father_node.qualifier
            method_decs = self.get_overload_method(father_node,var_dict)
            father_return_class = method_decs[2]
        else:
            # undo 此处应考虑无对象直接调用静态方法的情况
            # 三层调用暂时忽略
            father_return_class = None
        return father_return_class

    def load_pkl(self, path):
        with open(path, 'rb') as f:
            data = pickle.load(f)
        return data
    # def varname2pack(self, var_name, var_dict):
    def get_overload_method(self, node, var_dict):
        try:
            var_name = node.qualifier
            method_list = var_dict[var_name][1]
            overload_method = [method for method in method_list if method[0] == node.member]
            # undo 当重叠调用时，参数包含MethodInvocation，和MemberReference两种
            if len(overload_method) > 1:
                # 参数类型只包含java基本类型和标准库类
                # undo 如果参数为泛型的话，参数的类型可能为自定义类，该情况暂时抛弃
                # undo 如果参数中包含方法调用，则暂时抛弃
                argu_type_list = list()
                for argument in node.arguments:
                    if isinstance(argument,Tree.MemberReference):
                        argu_type_list.append(var_dict.get(argument.member))
                    else:
                        raise TypeExceptin("如果参数中包含方法调用，则暂时抛弃")
                # undo 此处应多次测试，并改用for循环比较每一项，防止出现泛型
                right_method = [method for method in overload_method if operator.eq(method[1],argu_type_list)]
                if not right_method:
                    raise TypeExceptin("没有找到匹配的重载函数")

            if len(overload_method) == 1:
                right_method = overload_method[0]
            # 返回类型：[方法名，[参数]，返回值]
            return right_method
        except TypeExceptin as e:
            print(e.str)


    def parse(self, dirname):
        java_type = ['byte', 'char', 'short', 'int', 'long', 'float', 'double', 'boolean']
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
                    # {参数名，[包名.类名,[参数列表]]}
                    var_dict = dict()
                    api_list = list()
                    class_pack_dict = dict()
                    for path, node in tree:
                        # print(path, node)
                        # 提取导入类，并获得包信息
                        class_meths_dict = class_pack_dict
                        if isinstance(node,Tree.Import):
                            # undo .*情况node.path没有*
                            # class_pack_dict   类名 -》 [包和[所有方法[方法名，参数（可能为none），返回值（可能为void）]]]
                            # 需要判断该引用是否是标准库
                            if pack_dict.__contains__(node.path):
                                pack_contain_class = pack_dict.get(pack_name)
                                class_meths_dict.update(pack_contain_class)
                            else:
                                pakage_list = node.path.split('.')
                                class_name = pakage_list[len(pakage_list) - 1]
                                pack_name = pakage_list[0]
                                for i in range(1, len(pakage_list) - 1):
                                    pack_name += pakage_list[i]
                                class_meths_dict[class_name] = pack_dict.get(pack_name).get(class_name)
                        #通过path获得局部变量定义，未确定类
                        if isinstance(node, Tree.VariableDeclarator):
                            path_len = len(path) - 1
                            if isinstance(path[path_len], list):
                                path_len -= 1
                            # var_dict[node.name] = path[path_len].type.name
                            var_class_name = path[path_len].type.name
                            if class_meths_dict.__contains__(var_class_name):
                                var_dict[node.name] = [f'{pack_name}.{class_name}', class_meths_dict.get(var_class_name)]
                            # 在这里加入java基本类型变量，为参数判断准备
                            if var_class_name in java_type:
                                var_dict[node.name] = var_class_name
                        # 形参，获取变量名及类
                        if isinstance(node, Tree.FormalParameter):
                            # var_dict[node.name] = node.type.name
                            par_class_name = node.type.name
                            if class_meths_dict.__contains__(par_class_name):
                                var_dict[node.name] = [f'{pack_name}.{class_name}', class_meths_dict.get(par_class_name)]
                        # 方法调用，须与变量名关联，变量名与类关联，类与包信息关联
                        if isinstance(node, Tree.MethodInvocation) and (var_dict.__contains__(node.qualifier)):
                            var_name = node.qualifier
                            # 多级调用，
                            if not var_name:
                                var_father_return_class = self.get_father_return_class(path, var_dict, node)
                                if (not var_name is None) :
                                    method_decs = self.get_overload_method(node, var_dict)
                                    api_list.append(f'{var_father_return_class}.{method_decs[0]}{method_decs[1]}')
                            else:
                                method_class = var_dict[var_name][0]
                                method_decs = self.get_overload_method(node, var_dict)
                                api_list.append(f'{method_class}.{method_decs[0]}{method_decs[1]}')
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



