import os

import javalang
import javalang.tree as Tree
import os, pickle
import re
import networkx as nx

class TypeExceptin(Exception):
    "this is user's Exception for check the length of name "
    def __init__(self,str):
        self.str = str
    def __str__(self):
        print("该情况暂未处理:"+self.str)

class MethodNestingExceptin(Exception):
    "this is user's Exception for check the length of name "
    def __init__(self,str):
        self.str = str
    def __str__(self):
        print("方法嵌套:"+self.str)


class AST_parse():
    def __init__(self):
        # 存储所有控制流语句节点 path索引 -> [node,father_api,children_api,False],false代表father是否和控制语句的第一个api链接
        self.control_node_dict = dict()
        # {参数名，[包名.类名,[参数列表]]}
        self.var_dict = dict()
        self.last_api = -1
        self.now_api = None
        self.neighbor_dict = dict()
        self.all_neighbor_dict = list()
        self.api_list = list()
        self.all_api_list = list()
        self.G = nx.Graph()
        self.all_path = list()

    def get_father_return_class(self, path, node):
        path_len = len(path) - 1
        if isinstance(path[path_len], list):
            path_len -= 1
        father_node = path[path_len]
        # undo 如果是两层掉用，则拿到第二层的变量
        # 如果不包含在self.var_dict中，说明不是标准库函数
        if hasattr(father_node, 'qualifier') and (self.var_dict.__contains__(father_node.qualifier)):
            method_decs = self.get_overload_method(father_node)
            father_return_class = method_decs[2]
        else:
            father_return_class = None
        # 返回格式 包+类名
        return father_return_class

    def load_pkl(self, path):
        with open(path, 'rb') as f:
            data = pickle.load(f)
        return data

    # undo 查询字面常量Literal是int,float,double,String,char[]中的哪一种
    def judge_Literal(self, node):
        literal = node.value
        type_name = None
        if literal[0] == '\'' and literal[-1:] == '\'':
            type_name = 'char[]'
        elif literal[0] == '\"' and literal[-1:] == '\"':
            type_name = 'java.lang.String'
        elif literal == 'true' or literal == 'false':
            type_name = 'boolean'
        elif re.compile(r'^[-+]?[0-9]+$').match(literal):
            type_name = 'int'
        elif re.compile(r'^[-+]?[0-9]+\.[0-9]+$').match(literal):
            type_name = 'float'
        return type_name

    # 通过函数调用节点的方法名及参数，查询出符合的库函数
    def get_overload_method(self, node):
        try:
            var_name = node.qualifier
            method_list = self.var_dict[var_name][1]
            overload_method = [method for method in method_list if method[0] == node.member]
            # undo 当重叠调用时，参数包含MethodInvocation，和MemberReference两种
            if len(overload_method) > 1:
                # 参数类型只包含java基本类型和标准库类
                # undo 如果参数为泛型的话，参数的类型可能为自定义类，该情况暂时抛弃
                # undo 如果参数中包含方法调用，则暂时抛弃
                argu_type_list = list()
                for argument in node.arguments:
                    if isinstance(argument,Tree.MemberReference):
                        argu_type_list.append(self.var_dict.get(argument.member)[0])
                    elif isinstance(argument,Tree.Literal):
                        argu_type_list.append(self.judge_Literal(argument))
                    else:
                        raise MethodNestingExceptin("如果参数中包含方法调用，则随即返回一个参数数量相等的方法")

                # undo 此处应多次测试，并改用for循环比较每一项，防止出现泛型
                # right_method = [method for method in overload_method if (method[1].split(',') == argu_type_list)]
                right_method = None
                for method in overload_method:
                    if method[1].split(',') == argu_type_list:
                        right_method = method
                if not right_method:
                    raise MethodNestingExceptin(f"{self.var_dict[var_name][0]}.{node.member}没有找到匹配的重载函数")

            elif len(overload_method) == 1:
                right_method = overload_method[0]
            else: right_method = None
            # 返回类型：[方法名，[参数]，返回值]
            return right_method
        except TypeExceptin as e:
            print(e.str)
        except MethodNestingExceptin:
            argu_num = len(node.arguments)
            right_method = [method for method in overload_method if (len(method[1].split(',')) == argu_num)][0]
            return right_method
        except BaseException:
            pass

    # 每当添加新api时
    def update_control_dict(self, path, node):
        # 邻接表新建一行
        now_api_num = len(self.api_list) - 1
        self.G.add_node(now_api_num)
        self.neighbor_dict[now_api_num] = set()
        # 如果没有控制节点且有上一个api
        if not self.control_node_dict.keys() and self.last_api > -1:
            self.neighbor_dict.get(self.last_api).add(now_api_num)
            self.G.add_edge(self.last_api, now_api_num)
        for key in list(self.control_node_dict.keys()):
            # 如果控制节点被弹出，即该循环结束
            control_node = self.control_node_dict.get(key)
            if len(path) <= key or not path[key] == control_node[0]:
                control_node[2] = now_api_num
                if not control_node[1] == -1:
                    self.neighbor_dict.get(control_node[1]).add(control_node[2])
                    self.G.add_edge(control_node[1], control_node[2])
                # 证明该循环中没有api
                if not control_node[3]:
                    # 环
                    if isinstance(control_node[0], Tree.WhileStatement) or isinstance(control_node[0], Tree.ForStatement):
                        self.neighbor_dict.get(control_node[3]).add(self.last_api)
                        self.G.add_edge(self.control_node[3], self.last_api)
                    self.neighbor_dict.get(self.last_api).add(control_node[2])
                    self.G.add_edge(self.last_api, control_node[2])
                self.control_node_dict.pop(key)
            # 如果循环还未结束，则链接fater和循环中第一个api
            elif self.last_api == -1:
                control_node[3] = False
            elif control_node[3]:
                control_node[4] = now_api_num
                self.neighbor_dict.get(control_node[1]).add(now_api_num)
                self.G.add_edge(control_node[1], now_api_num)
                control_node[3] = False
            else:
                self.neighbor_dict.get(self.last_api).add(now_api_num)
                self.G.add_edge(self.last_api, now_api_num)
        self.last_api = now_api_num

    def parse(self, dirname):
        java_type = ['byte[]', 'char', 'short', 'int', 'long', 'float', 'double', 'boolean']
        file_handle = open('1.txt', mode='w')
        file_handle.truncate(0)
        for maindir, subdir, file_name_list in os.walk(dirname):
            for java_file in file_name_list:
                if java_file.endswith('.java'):
                    apath = os.path.join(maindir, java_file)
                    f_input = open(apath, 'r', encoding='utf-8')
                    tree = javalang.parse.parse(f_input.read())
                    pack_dict = self.load_pkl('api2desc.pkl')
                    import_dict = dict()
                    class_meths_dict = dict()
                    # 存储控制流语句的上一个api和和当前api
                    # undo 核心包java.lang默认导入
                    class_meths_dict.update(pack_dict.get('java.lang'))
                    for class_name in class_meths_dict.keys():
                        import_dict[class_name] = 'java.lang'
                    for path, node in tree:
                        # print(path, node)
                        # print(node)
                        # 所有条件语句，待补充
                        # # 如过父亲节点中包含条件条件语句，则不予执行
                        # 提取导入类，并获得包信息
                        if isinstance(node, Tree.Import):
                            # undo .*情况node.path没有*
                            # class_pack_dict   类名 -》 [包和[所有方法[方法名，参数（可能为none），返回值（可能为void）]]]
                            # 需要判断该引用是否是标准库
                            if pack_dict.__contains__(node.path):
                                pack_contain_class = pack_dict.get(node.path)
                                class_meths_dict.update(pack_contain_class)
                                for class_name in pack_contain_class.keys():
                                    import_dict[class_name] = node.path
                            else:
                                pakage_list = node.path.split('.')
                                class_name = pakage_list[len(pakage_list) - 1]
                                pack_name = pakage_list[0]
                                for i in range(1, len(pakage_list) - 1):
                                    pack_name += f'.{pakage_list[i]}'
                                if pack_dict.__contains__(pack_name):
                                    class_meths_dict[class_name] = pack_dict.get(pack_name).get(class_name)
                                    import_dict[class_name] = pack_name

                        # 为应对静态变量
                        elif isinstance(node, Tree.ClassDeclaration):
                            for class_name in class_meths_dict.keys():
                                pack_name = import_dict.get(class_name)
                                self.var_dict[class_name] = [f'{pack_name}.{class_name}', class_meths_dict.get(class_name)]

                        elif isinstance(node, Tree.MethodDeclaration):
                            self.all_api_list.append(list(self.api_list))
                            # 把索引转为api，之所以用索引是因为api有重名的
                            for num_path in nx.all_simple_paths(self.G, source=0, target=len(self.G.nodes)-1):
                                api_path = list()
                                for num_api in num_path:
                                    api_path.append(self.api_list[num_api])
                                self.all_path.append(api_path)
                            self.G.clear()
                            self.api_list.clear()
                            self.all_neighbor_dict.append(dict(self.neighbor_dict))
                            self.neighbor_dict.clear()
                            self.control_node_dict.clear()
                            self.last_api = -1


                        elif isinstance(node, Tree.IfStatement) or isinstance(node, Tree.WhileStatement) or isinstance(node, Tree.ForStatement):
                            # 如果新的path长度恰好和之前相等，那么就会被覆盖
                            self.control_node_dict[len(path)] = [node, self.last_api, None, True, None]

                        #通过path获得局部变量定义，未确定类
                        elif isinstance(node, Tree.VariableDeclarator):
                            path_len = len(path) - 1
                            if isinstance(path[path_len], list):
                                path_len -= 1
                            var_class_name = path[path_len].type.name
                            if class_meths_dict.__contains__(var_class_name):
                                pack_name = import_dict.get(var_class_name)
                                self.var_dict[node.name] = [f'{pack_name}.{var_class_name}', class_meths_dict.get(var_class_name)]
                            # 在这里加入java基本类型变量，为参数判断准备
                            if var_class_name in java_type:
                                self.var_dict[node.name] = var_class_name

                        # 形参，获取变量名及类
                        elif isinstance(node, Tree.FormalParameter):
                            par_class_name = node.type.name
                            if class_meths_dict.__contains__(par_class_name):
                                self.var_dict[node.name] = [f'{pack_name}.{class_name}', class_meths_dict.get(par_class_name)]
                        # 方法调用，须与变量名关联，变量名与类关联，类与包信息关联
                        # undo 多级调用根本没进来
                        elif isinstance(node, Tree.MethodInvocation):
                            print(node)
                            if node.member == 'write':
                                print('a')
                            if self.var_dict.__contains__(node.qualifier):
                                # print(node)
                                var_name = node.qualifier
                                method_class = self.var_dict[var_name][0]
                                method_decs = self.get_overload_method(node)
                                self.api_list.append(f'{method_class}.{method_decs[0]}({method_decs[1]})')

                                self.update_control_dict(path, node)
                            # 当连续调用
                            elif not node.qualifier:
                                var_father_return_class = self.get_father_return_class(path, node)
                                if not var_father_return_class is None:
                                    # 当父节点方法返回值为None
                                    if var_father_return_class == 'None.E':
                                        self.api_list.append(f'E.{node.member}(UNKNOW)')
                                        self.update_control_dict(path, node)
                                    # 当父节点返回为正常类
                                    else:
                                        node.qualifier = var_father_return_class.split('.')[-1]
                                        # 当父节点返回为正常类
                                        if node.qualifier in import_dict.keys():
                                            method_decs = self.get_overload_method(node)
                                            self.api_list.append(f'{var_father_return_class}.{method_decs[0]}({method_decs[1]})')
                                            self.update_control_dict(path, node)
                        file_handle.write('path=' + str(path) + '\n')
                        file_handle.write('node=' + str(node) + '\n'+ '\n'+ '\n')
        print(self.all_api_list)
        print(self.all_neighbor_dict)
        print(self.all_path)
        file_handle.close()




if __name__ == '__main__':
    my_parse = AST_parse()
    my_parse.parse('demo_test')


# undo UNKNOW 已解决
# undo 两个局部变量名字一样怎么办 ,已解决
# undo CatchClauseParameter(annotations=None, modifiers=None, name=e, types=['IOException']
# undo 方法间的调用顺序  do


# undo 循环调用 已解决
# undo 多类测试
# undo 返回值，参数问题  java.util.Arrays.asList(T...)
# undo raplase为什么不在里面
# undo 生成路径 do
# undo 循环