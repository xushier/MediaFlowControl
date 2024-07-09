#!/usr/bin/env python3
# _*_ coding:utf-8 _*_


from __notifier import one, wecom_app

def notify_template(title, item, font_color="white", border_color = "#a35c8f", title_color="#8A3782", head_color="#681752", item_color_A="#894276", item_color_B = "#7e2065"):
    font_color   = font_color
    border_color = border_color
    title_color  = title_color
    head_color   = head_color
    item_color_A = item_color_A
    item_color_B = item_color_B
    title  = title
    item   = item
    colume = "2"

    content_title = f"""
        <table style="border-radius: 25px;border: 1px solid {border_color};overflow: hidden;font-size: 14px;font-weight: 500;font-family: -apple-system-font, BlinkMacSystemFont, 'Helvetica Neue', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei UI', 'Microsoft YaHei', Arial;border-collapse: collapse;width: 100%;letter-spacing: 1px;text-align: center;">
            <tr style="border: 1px solid {border_color};background-color: {title_color};color: {font_color};font-size: 18px;">
                <th colspan={colume} style="padding: 8px;">{title}</td>
            </tr>
    """

    content_head = f"""
            <tr style="border: 1px solid {border_color};background-color: {head_color};color: {font_color};font-size: 16px;">
                <th style="padding: 8px;padding-top: 12px;padding-bottom: 12px;">项目</th>
                <th style="padding: 8px;padding-top: 12px;padding-bottom: 12px;">状态</th>
            </tr>
    """

    content_item = ""
    for index, key in enumerate(item):
        if index % 2 == 0:
            bk_color = item_color_A
        else:
            bk_color = item_color_B
        content_item += f"""
            <tr style="border: 1px solid {border_color};background-color: {bk_color};color: {font_color};">
                <td style="padding: 8px;">{key}</td>
                <td style="padding: 8px;">{item[key]}</td>
            </tr>
        """

    content_end = one()
    content_end = f"""
            <tr style="border: 1px solid {border_color};background-color: {title_color};color: {font_color};">
                <td colspan={colume} style="padding: 8px;padding-left: 15px;padding-right: 15px;"><p style="text-align: left;">{content_end[0]}</p><p style="text-align: right;">———{content_end[1]}</p></td>
            </tr>
        </table>
    """
    return content_title + content_head + content_item + content_end



def notify_template_col4(title, item, font_color="white", border_color = "#a35c8f", title_color="#8A3782", head_color="#681752", item_color_A="#894276", item_color_B = "#7e2065", info=False, info_content="", title1="项目", title2="状态"):
    font_color   = font_color
    border_color = border_color
    title_color  = title_color
    head_color   = head_color
    item_color_A = item_color_A
    item_color_B = item_color_B
    title  = title
    item = item
    colume = "4"

    content_title = f"""
        <table style="border-radius: 25px;border: 1px solid {border_color};overflow: hidden;font-size: 14px;font-weight: 500;font-family: -apple-system-font, BlinkMacSystemFont, 'Helvetica Neue', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei UI', 'Microsoft YaHei', Arial;border-collapse: collapse;width: 100%;letter-spacing: 1px;text-align: center;">
            <tr style="border: 1px solid {border_color};background-color: {title_color};color: {font_color};font-size: 18px;">
                <th colspan={colume} style="padding: 8px;">{title}</td>
            </tr>
    """

    content_head = f"""
            <tr style="border: 1px solid {border_color};background-color: {head_color};color: {font_color};font-size: 16px;">
                <th style="padding: 8px;padding-top: 12px;padding-bottom: 12px;width: 25%;">{title1}</th>
                <th style="padding: 8px;padding-top: 12px;padding-bottom: 12px;border-right: 2px dotted {border_color};width: 25%;">{title2}</th>
                <th style="padding: 8px;padding-top: 12px;padding-bottom: 12px;width: 25%;">{title1}</th>
                <th style="padding: 8px;padding-top: 12px;padding-bottom: 12px;width: 25%;">{title2}</th>
            </tr>
    """

    content_item = ""
    for index, key in enumerate(item):
        if index % 2 != 0:
            continue
        if index % 4 == 0:
            bk_color = item_color_A
        else:
            bk_color = item_color_B
        first = item[index]
        if index+1 == len(item):
            second = ('小迪', '666')
        else:
            second = item[index+1]
        content_item += f"""
            <tr style="border: 1px solid {border_color};background-color: {bk_color};color: {font_color};">
                <td style="padding: 8px;">{first[0]}</td>
                <td style="padding: 8px;border-right: 2px dotted {border_color};">{first[1]}</td>
                <td style="padding: 8px;">{second[0]}</td>
                <td style="padding: 8px;">{second[1]}</td>
            </tr>
        """

    if info:
        if bk_color == item_color_A:
            bk_color = item_color_B
        else:
            bk_color = item_color_A
        if info_content:
            content_item += f"""
                <tr style="border: 1px solid {border_color};background-color: {bk_color};color: {font_color};text-align: left;">
                    <td colspan={colume} style="padding: 8px;padding-left: 15px;padding-right: 15px;">{info_content}</td>
                </tr>
            """

    content_end = one()
    content_end = f"""
            <tr style="border: 1px solid {border_color};background-color: {title_color};color: {font_color};">
                <td colspan={colume} style="padding: 8px;padding-left: 15px;padding-right: 15px;"><p style="text-align: left;">{content_end[0]}</p><p style="text-align: right;">———{content_end[1]}</p></td>
            </tr>
        </table>
    """
    return content_title + content_head + content_item + content_end

