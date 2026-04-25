from manim import *
import numpy as np
from manim.utils.rate_functions import ease_in_quart

class ProbabilityDensityAnimation1(Scene):
    def construct(self):
        #调试位置时使用的坐标轴系统
        # number_plane = NumberPlane(
        #     background_line_style={
        #         "stroke_color": GREY,
        #         "stroke_width": 2,
        #         "stroke_opacity": 0.2
        #     }
        # )
        # self.add(number_plane)

        # 动画1：题目文字
        title = Tex(
            r"二维随机变量$(X,Y)$概率密度函数为$z=\begin{cases}\mathrm{e}^{-x}\mathrm{e}^{-y},&x>0,y>0\\0,&others\\\end{cases}$,",
            r"设$Z=XY$，请求出$z$的概率密度函数$f_Z(z)$",
            tex_template=TexTemplateLibrary.ctex,
            font_size=32
        ).to_edge(UP)
        self.play(Write(title))
        self.wait(1)

        # 动画2：创建二维坐标系
        axes = Axes(
            x_range=[0, 5, 1],
            y_range=[0, 5, 1],
            x_length=4.5,
            y_length=4.5,
            axis_config={"include_numbers": True},
            tips=True
        ).to_corner(DL)
        self.play(Create(axes))

        # 动画3：将{x>0, y>0}区域涂上渐变灰色
        # 定义颜色渐变函数
        def get_gray_color(value, vmin=0, vmax=25):
            alpha = np.clip((value - vmin) / (vmax - vmin), 0, 1)  # 归一化到 [0, 1]
            return interpolate_color(WHITE, DARK_GRAY, alpha)

        # 遍历 {x>0, y>0} 区域并涂色
        shading_group = VGroup()
        for x in np.linspace(0, 5, 50):
            for y in np.linspace(0, 5, 50):
                if x > 0 and y > 0:
                    color = get_gray_color(x * y)
                    square = Square(side_length=0.1).move_to(axes.c2p(x, y))
                    square.set_fill(color, opacity=0.5).set_stroke(width=0)
                    shading_group.add(square)
        self.play(FadeIn(shading_group))
        # 创建黑色遮罩，避免画图出边界
        mask_top = Rectangle(width=14, height=5, color=BLACK, fill_opacity=1).next_to((0,1.6,0),UP)
        mask_top.set_z_index(1)
        title.set_z_index(2)
        self.add(mask_top)
        self.wait(1)

        # 动画4：右侧显示公式
        a_tracker = ValueTracker(0.5)  # 定义参数 a
        a_text = always_redraw(lambda: MathTex(
            rf"P\{{XY<{a_tracker.get_value():.1f}\}} = P\{{Z<{a_tracker.get_value():.1f}\}}=F_Z\left({a_tracker.get_value():.1f}\right)",
            tex_template=TexTemplateLibrary.ctex,
            font_size=36
        ).next_to(axes,RIGHT).move_to(RIGHT*3))
        self.play(Write(a_text))
        self.wait(1)


        # 动画5：绘制 y = a/x 曲线和黄色区域
        curve = always_redraw(lambda: axes.plot(
            lambda x: a_tracker.get_value() / x if x > 0 else 0,  # y = a / x
            x_range=[0.1, 5],  # 避免除以 0
            color=YELLOW
        ))

        # 使用 get_area 填充区域
        area = always_redraw(lambda: axes.get_area(
            curve,
            x_range=[0.1, 5],  # 填充的区域范围
            color=YELLOW,
            opacity=0.5
        ))

        area.set_z_index(0)

        # 为黄色区域添加数学公式 Z<a
        area_label = always_redraw(lambda: MathTex(
            rf"XY<{a_tracker.get_value():.1f}",
            tex_template=TexTemplateLibrary.ctex,
            font_size=32,
            color=BLACK
        ).move_to(axes.c2p(1, 1))).set_z_index(1)  # 在区域内适合的位置显示公式

        self.play(Create(curve), FadeIn(area), Write(area_label))

        # 动画6：参数 a 从 0.5 增长
        self.play(a_tracker.animate.set_value(10), run_time=8, rate_func=linear)

        # 结束动画
        self.wait(2)

class ProbabilityDensityAnimation2(Scene):
    def construct(self):
        # number_plane = NumberPlane(
        #     background_line_style={
        #         "stroke_color": GREY,
        #         "stroke_width": 2,
        #         "stroke_opacity": 0.2
        #     }
        # )
        # self.add(number_plane)

        # 动画1：题目文字
        title = Tex(
            r"二维随机变量$(X,Y)$概率密度函数为$z=\begin{cases}\mathrm{e}^{-x}\mathrm{e}^{-y},&x>0,y>0\\0,&others\\\end{cases}$,",
            r"设$Z=Y/X$，请求出$z$的概率密度函数$f_Z(z)$",
            tex_template=TexTemplateLibrary.ctex,
            font_size=32
        ).to_edge(UP)
        self.play(Write(title))
        self.wait(1)

        # 动画2：创建二维坐标系
        axes = Axes(
            x_range=[0, 5, 1],
            y_range=[0, 5, 1],
            x_length=4.5,
            y_length=4.5,
            axis_config={"include_numbers": True},
            tips=True
        ).to_corner(DL)
        self.play(Create(axes))

        # 动画3：将{x>0, y>0}区域涂上渐变灰色
        # 定义颜色渐变函数
        def get_gray_color(value, vmin=0, vmax=25):
            alpha = np.clip((value - vmin) / (vmax - vmin), 0, 1)  # 归一化到 [0, 1]
            return interpolate_color(WHITE, DARK_GRAY, alpha)

        # 遍历 {x>0, y>0} 区域并涂色
        shading_group = VGroup()
        for x in np.linspace(0, 5, 50):
            for y in np.linspace(0, 5, 50):
                if x > 0 and y > 0:
                    color = get_gray_color(x * y)
                    square = Square(side_length=0.1).move_to(axes.c2p(x, y))
                    square.set_fill(color, opacity=0.5).set_stroke(width=0)
                    shading_group.add(square)
        self.play(FadeIn(shading_group))
        # 创建黑色遮罩，避免画图出边界
        mask_top = Rectangle(width=14, height=5, color=BLACK, fill_opacity=1).next_to((0,1.6,0),UP)
        mask_top.set_z_index(1)
        title.set_z_index(2)
        self.add(mask_top)
        self.wait(1)

        # 动画4：右侧显示公式
        a_tracker = ValueTracker(0.5)  # 定义参数 a
        a_text = always_redraw(lambda: MathTex(
            rf"P\{{Y/X<{a_tracker.get_value():.1f}\}} = P\{{Z<{a_tracker.get_value():.1f}\}}=F_Z\left({a_tracker.get_value():.1f}\right)",
            tex_template=TexTemplateLibrary.ctex,
            font_size=36
        ).next_to(axes,RIGHT).move_to(RIGHT*3))
        self.play(Write(a_text))
        self.wait(1)

        # 动画5：绘制 y = ax 曲线和黄色区域
        curve = always_redraw(lambda: axes.plot(
            lambda x: a_tracker.get_value() * x,
            x_range=[0, 5],  # 避免除以 0
            color=YELLOW
        ))

        # 使用 get_area 填充区域
        area = always_redraw(lambda: axes.get_area(
            curve,
            x_range=[0, 5],  # 填充的区域范围
            color=YELLOW,
            opacity=0.5
        ))

        area.set_z_index(0)
        self.wait(1)

        # 为黄色区域添加数学公式 Z<a
        area_label = always_redraw(lambda: MathTex(
            rf"Y/X<{a_tracker.get_value():.1f}",
            tex_template=TexTemplateLibrary.ctex,
            font_size=32,
            color=BLACK
        ).move_to(axes.c2p(3.5, 1))).set_z_index(1)  # 在区域内适合的位置显示公式

        self.play(Create(curve), FadeIn(area), Write(area_label))

        # 动画6：参数 a 从 0.5 增长
        self.play(a_tracker.animate.set_value(10), run_time=8, rate_func=ease_in_quart)

        # 结束动画
        self.wait(2)