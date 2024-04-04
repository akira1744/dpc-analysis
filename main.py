import streamlit as st
import altair as alt
from altair import limit_rows, to_values
import toolz

from package import myfunc


def t(data):
    return toolz.curried.pipe(data, limit_rows(max_rows=300000), to_values)


st.set_page_config(layout="wide")

alt.data_transformers.register("custom", t)
alt.data_transformers.enable("custom")

# get mst
region_list, mdcname_list, mdc6name_list = myfunc.get_mst()

# sidebar
st.sidebar.markdown("## 2022年度DPC退院患者調査")
st.sidebar.markdown("### ")

# regionのセレクトボックス
select_region = st.sidebar.selectbox("地方", region_list, index=2)

# regionのデータを取得
pref_list, hp_list, hp = myfunc.get_region_data(select_region)

# sidebarの処理
select_prefs, select_med2s, select_citys, select_hpname, hp = myfunc.set_location(
    pref_list, hp_list, hp
)
# sidebarの病床数を取得
set_min, set_max = st.sidebar.slider("病床数", value=(0, 1400), step=50)

# 最後にbedでフィルタリングしてからselect_hpcdを取得
select_hpcd = myfunc.get_select_hpcd(hp, select_hpname, set_min, set_max)

# data取得
mdc2d, mdc6d, oped = myfunc.get_value_data(
    select_hpcd, select_hpname, hp_list, mdcname_list, mdc6name_list
)

# mdc2dが0件だった場合、myfunc.draw_chart()は実行せずに、該当の病院はありませんと表示
if len(mdc2d) == 0:
    st.write("該当の病院はありません。検索条件を再設定してください。")
else:
    charts = myfunc.draw_chart(select_hpname, mdc2d, mdc6d, oped)
    st.altair_chart(charts)


# フッター　###################################################################################
link1 = "https://www.mhlw.go.jp/stf/shingi2/newpage_39119.html"
link2 = "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000198757_00004.html"


my_expander = st.expander("DataSource")
with my_expander:
    st.markdown(
        "[1.令和4年度DPC導入の影響評価に係る調査「退院患者調査」の結果報告について]({})".format(
            link1
        )
    )
    st.markdown(
        "[2.診断群分類（DPC）電子点数表（正式版）（令和5年12月19日更新）]({}) ".format(
            link2
        )
    )

my_expander = st.expander("Q & A")
with my_expander:
    st.markdown("Q. 院内の実績値と異なる")
    st.markdown(
        """
    A. 厚労省の退院患者調査では、実績が10件未満のデータが公開されていない為、実績値よりも低い数字が表示されます。"""
    )
