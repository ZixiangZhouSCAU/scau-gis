import arcpy
import sys
import numpy

#取得参数
inWorkspace = arcpy.GetParameterAsText(0)
inFeature = arcpy.GetParameterAsText(1)
inField = arcpy.GetParameterAsText(2)
outTable = arcpy.GetParameterAsText(3)

if not (inFeature and inField):
    arcpy.AddError("没有要素类或数值字段")
    sys.exit()

arcpy.env.workspace = inWorkspace
#存储多边形转点要素
'''
if arcpy.Exists("in_memory/cityPoints"):
    arcpy.Delete_management("in_memory/cityPoints")
#要素转点
try:
    arcpy.FeatureToPoint_management(inFeature, "in_memory/cityPoints", "INSIDE")
except Exception as e:
    arcpy.AddError("计算区域中心位置不成功,错误码："+e)
    sys.exit()
'''
#遍历所有点要素，计算两两之间的距离平方以及所代表城市的人口的乘积
curs1 = arcpy.da.SearchCursor(inFeature, ['OID@', 'SHAPE@X', 'SHAPE@Y', inField])
curs2 = arcpy.da.SearchCursor(inFeature, ['OID@', 'SHAPE@X', 'SHAPE@Y', inField])
PP = []
R2 = []
GIJ = []
for f1 in curs1:
    oid_1, x_1, y_1, p_1 = f1[0], f1[1], f1[2], f1[3]
    for f2 in curs2:
        oid_2, x_2, y_2, p_2 = f2[0], f2[1], f2[2], f2[3]
        if oid_2 != oid_1:
            rp = p_1*p_2
            PP.append(rp)
            rd = (x_1-x_2)**2 + (y_1-y_2)**2
            R2.append(rd)
            G = rp/rd
            l = len(GIJ)
            #当列表元素长度大于1时，需要判断两个城市之间引力是否已经计算，不需重复计算
            if l>0:
                e1 = [x[0] for x in GIJ] #列表推导式，获取列表中每个元组的第一个分量，以下类似
                e2 = [x[1] for x in GIJ]
                e3 = [x[2] for x in GIJ]
                tmpStr = str(oid_2)+'_'+str(oid_1) #拼接字符串标识两个城市的连接
                if e3.count(tmpStr) < 1:
                    GIJ.append((str(oid_1), str(oid_2),  str(oid_1)+'_'+str(oid_2), float(G)))
            else:
                GIJ.append((str(oid_1), str(oid_2), str(oid_1)+'_'+str(oid_2), float(G)))
    curs2.reset()
###使用numpy数组转化成表格数据
nArray = numpy.array(GIJ)
struct_array = numpy.core.records.fromarrays(nArray.transpose(),numpy.dtype([('City1', 'S32'), ('City2', 'S32'),('ComStr', 'S64'), ('Force', 'f8')]))
if arcpy.Exists(outTable):
    arcpy.Delete_management(outTable)
#将数组转换为表
arcpy.da.NumPyArrayToTable(struct_array, outTable)
#清除内存中存在的数据
arcpy.Delete_management("in_memory/cityPoints")

