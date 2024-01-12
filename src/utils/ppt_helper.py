import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_VERTICAL_ANCHOR, MSO_AUTO_SIZE
from pptx.oxml.xmlchemy import OxmlElement


def plot_graph(df, title, filter_col, output_name):
    """
    function to create plot chart.
    """
    # Reset the plt
    plt.figure(figsize=(16, 7))
    plt.bar(df[filter_col], df["dpo"], color="black")
    plt.bar(df[filter_col], df["dso"], color="red")
    plt.bar(df[filter_col], df["dio"], color="grey", bottom=df["dso"])
    plt.plot(df[filter_col], df["ccc"], color="black", marker="o")
    plt.ylabel("days", fontweight="bold", fontsize=15)
    plt.title(title)
    # plt.legend(df.columns.drop(filter_col))
    plt.legend(["ccc", "dpo", "dso", "dio"])
    plt.savefig(output_name)
    # remove the plt
    plt.clf()
    plt.cla()
    # plt.show()


def create_images_slide_two(df, slide, company_name):
    cols = ["dso", "dpo", "dio", "ccc"]

    # Calculate the rankings
    for col in cols:
        df[col + "_rank"] = df[col].rank()

    # Make all the numbers positive
    df.iloc[:, 1:] = df.iloc[:, 1:].abs()

    # Set Target company as the benchmark
    # benchmark = df[df["company"] == company_name].iloc[0, 1:]

    # Create the tables
    tables = []
    location = [
        [Inches(0.03), Inches(1.6), Inches(2), Inches(2)],
        [Inches(2.57), Inches(1.6), Inches(2), Inches(2)],
        [Inches(4.97), Inches(1.6), Inches(2), Inches(2)],
        [Inches(7.37), Inches(1.6), Inches(2), Inches(2)],
    ]

    for col in cols:
        table = df[["company", col, col + "_rank"]].sort_values(by=col + "_rank")
        table = table.reset_index(drop=True)
        table["rank"] = table.index + 1
        table = table[["company", col, "rank"]]
        table.index = table.index
        table = table.sort_index()

        table.loc[len(df)] = ["Peer Median", df[col].median(), ""]
        # table= pd.concat([pd.DataFrame({'company':['Dummy'], col: [0.0], 'Rank': [0]}), table])
        # table= pd.concat([pd.DataFrame({'company':['Dummy'], col: [0.0], 'Rank': [0]}), table])
        tables.append([col, table])

    txtTables = trial(tables, location, slide, company_name)

    return (txtTables, tables)


def SubElement(parent, tagname, **kwargs):
    element = OxmlElement(tagname)
    element.attrib.update(kwargs)
    parent.append(element)
    return element


def _set_cell_border(cell, border_color="#000000", border_width="12700"):
    """Hack function to enable the setting of border width and border color
    - top border
    - bottom border
    """
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()

    for lines in ["a:lnT", "a:lnB"]:
        # Every time before a node is inserted, the nodes with the same tag should be removed.
        tag = lines.split(":")[-1]
        for e in tcPr.getchildren():
            if tag in str(e.tag):
                tcPr.remove(e)

        ln = SubElement(tcPr, lines, w=border_width, cap="flat", cmpd="sng", algn="ctr")
        solidFill = SubElement(ln, "a:solidFill")
        SubElement(solidFill, "a:srgbClr", val=border_color)
        SubElement(ln, "a:prstDash", val="solid")
        SubElement(ln, "a:round")
        SubElement(ln, "a:headEnd", type="none", w="med", len="med")
        SubElement(ln, "a:tailEnd", type="none", w="med", len="med")

    return cell


def trial(tables, location, slide, company_name):
    txtTables = []
    tmp_i = -1
    for col, df in tables:
        tmp_i += 1
        # define the table dimensions
        rows, cols = df.shape
        rows += 1
        # define the table position and size
        left = location[tmp_i][0]
        top = location[tmp_i][1]
        width = location[tmp_i][2]
        height = location[tmp_i][3]

        # add the table to the slide
        table = slide.shapes.add_table(rows, cols, left, top, width, height).table

        # set the column widths
        table.columns[0].width = Inches(1.4)
        table.columns[1].width = Inches(0.6)
        table.columns[2].width = Inches(0.6)

        # add the table headers
        table.cell(0, 0).text = "Companies"
        table.cell(0, 1).text = col
        table.cell(0, 2).text = "Rank"

        imcd = [
            company_name,
            str(df[df["company"] == company_name][col].values[0]),
            str(df[df["company"] == company_name]["rank"].values[0]),
        ]
        df = df.drop(int(imcd[2]) - 1)

        ############################################
        # Comment this section to remove the warning
        ############################################
        # To add borders to the cells
        # for i in range(rows):
        #     for j in range(cols):
        #         cell = table.cell(i, j)
        #         cell = _set_cell_border(cell)
        ############################################
        ############################################

        for i in range(0, rows - 1):
            if i > 0:
                table.cell(i + 1, 0).text = str(df.iloc[i - 1, 0])
                table.cell(i + 1, 1).text = str(df.iloc[i - 1, 1])
                table.cell(i + 1, 2).text = str(df.iloc[i - 1, 2])

            if i == 0:
                for j in range(3):
                    table.cell(i, j).text_frame.paragraphs[0].font.bold = True

            if i < rows - 1:
                for j in range(3):
                    table.cell(i, j).fill.solid()
                    table.cell(i, j).fill.fore_color.rgb = RGBColor(255, 255, 255)  # white
                    table.cell(i, j).text_frame.paragraphs[0].font.color.rgb = RGBColor(0, 0, 0)

        for j in range(3):
            table.cell(rows - 1, j).fill.solid()
            table.cell(rows - 1, j).fill.fore_color.rgb = RGBColor(175, 175, 175)  # gray
            table.cell(rows - 1, j).text_frame.paragraphs[0].font.color.rgb = RGBColor(0, 0, 0)

        for j in range(3):
            table.cell(1, j).text = imcd[j]
            table.cell(1, j).text_frame.paragraphs[0].font.color.rgb = RGBColor(255, 0, 0)
            table.cell(1, j).text_frame.paragraphs[0].font.bold = True

        # Setting the font size of the table to 12
        for cell in table.iter_cells():
            for paragraph in cell.text_frame.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(10)  # set the font size to 12 points

        txtTables.append(table)

        # save the presentation
    return txtTables


# End: Functions
#################################################################


def ppt_generation(df, llm_insight, company_name, image_paths, output_path, n=6):
    """
    Function to generate the 2 ppt slide as template
    df: the benchmark table to be compare
    llm_insight: the insights generated by LLM on the company performance
    company_name: input of company name
    n: the ppt slide_layouts format, range from 0-9, 6 is a blank page

    Return: it is auto saved the ppt, so need FE to pick it up
    """
    image1 = image_paths[0]
    image2 = image_paths[1]

    # initial the property
    X = Presentation()

    # Create a new slide layout with a title and text box
    title_and_text_layout = X.slide_layouts[n]

    ##################################################################
    #   Start: First Slide
    first_slide = X.slides.add_slide(title_and_text_layout)

    # Remove the "Click to add title" box <- since we changed it to a blank page so this can be removed
    # first_slide.shapes.title.text = " "

    # Add a title to the slide
    title_shape = first_slide.shapes.add_textbox(Inches(0.5), Inches(0), Inches(9), Inches(1))
    title_shape.text = "Working Capital - ccc Trend & Peer Comparison"
    title_shape.text_frame.paragraphs[0].font.name = "Univers Next for HSBC Bold"
    title_shape.text_frame.paragraphs[0].font.bold = True
    title_shape.text_frame.paragraphs[0].font.size = Pt(24)
    title_shape.text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    title_shape.text_frame.vertical_anchor = MSO_VERTICAL_ANCHOR.MIDDLE

    # Adding 1st Image with border
    pic = first_slide.shapes.add_picture(image1, Inches(1), Inches(1), width=Inches(8), height=Inches(2.8))
    pic.line.width = Pt(1)
    pic.line.color.rgb = RGBColor(225, 225, 225)

    # Adding 2nd Image with border
    pic = first_slide.shapes.add_picture(image2, Inches(1), Inches(3.95), width=Inches(8), height=Inches(2.8))
    pic.line.width = Pt(1)
    pic.line.color.rgb = RGBColor(225, 225, 225)

    # Adding a text box with "Source" text
    source_textbox = first_slide.shapes.add_textbox(Inches(0.9), Inches(6.75), Inches(2), Inches(0.5))
    source_textbox.text = "Source: S&P Capital IQ"
    source_textbox.text_frame.paragraphs[0].font.name = "Univers Next for HSBC Light"
    source_textbox.text_frame.paragraphs[0].font.size = Pt(10.1)
    source_textbox.text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    source_textbox.text_frame.vertical_anchor = MSO_VERTICAL_ANCHOR.MIDDLE

    #    End: First Slide
    ##################################################################

    ##################################################################
    #   Start: Second Slide
    second_slide = X.slides.add_slide(title_and_text_layout)

    # Load the data from the Excel files
    df["company"] = df["company"].str.strip()
    df = df[df["company"] != "Peer Group (Median)"]
    # Fill empty cells with ""
    df = df.fillna("")

    # Putting the tables in the presentation
    create_images_slide_two(df, second_slide, company_name)

    # Remove the "Click to add title" box <- since we changed it to a blank page so this can be remved
    # second_slide.shapes.title.text = " "

    # Add a Heading to the slide
    title_shape = second_slide.shapes.add_textbox(Inches(0.5), Inches(0), Inches(9), Inches(1))
    title_shape.text = "Relative Working Capital Efficiency Against Peer Group"
    title_shape.text_frame.paragraphs[0].font.name = "Univers Next for HSBC Bold"
    title_shape.text_frame.paragraphs[0].font.bold = True
    title_shape.text_frame.paragraphs[0].font.size = Pt(24)
    title_shape.text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    title_shape.text_frame.vertical_anchor = MSO_VERTICAL_ANCHOR.MIDDLE

    # Adding a text box with "Sub-Heading" text
    source_textbox = second_slide.shapes.add_textbox(Inches(0.5), Inches(1), Inches(2), Inches(0.5))
    source_textbox.text = "Working Capital Efficiency Rankings"
    source_textbox.text_frame.paragraphs[0].font.name = "Univers Next for HSBC Light"
    source_textbox.text_frame.paragraphs[0].font.bold = True
    source_textbox.text_frame.paragraphs[0].font.size = Pt(15.1)
    source_textbox.text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    source_textbox.text_frame.vertical_anchor = MSO_VERTICAL_ANCHOR.MIDDLE

    # Adding a text box with "Source" text
    source_textbox = second_slide.shapes.add_textbox(Inches(0.5), Inches(3.8), Inches(2), Inches(0.5))
    source_textbox.text = "Source: S&P Capital IQ"
    source_textbox.text_frame.paragraphs[0].font.name = "Univers Next for HSBC Light"
    source_textbox.text_frame.paragraphs[0].font.size = Pt(10.1)
    source_textbox.text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    source_textbox.text_frame.vertical_anchor = MSO_VERTICAL_ANCHOR.MIDDLE

    # Adding a text box with "Key Insigts" text
    source_textbox = second_slide.shapes.add_textbox(Inches(0.5), Inches(4.3), Inches(2), Inches(0.5))
    source_textbox.text = "Key Insights"
    source_textbox.text_frame.paragraphs[0].font.name = "Univers Next for HSBC Light"
    source_textbox.text_frame.paragraphs[0].font.bold = True
    source_textbox.text_frame.paragraphs[0].font.size = Pt(15.1)
    source_textbox.text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    source_textbox.text_frame.vertical_anchor = MSO_VERTICAL_ANCHOR.MIDDLE
    # Adding a text box with Key Insigts information
    source_textbox = second_slide.shapes.add_textbox(Inches(0.6), Inches(4.8), Inches(8), Inches(2))
    paragraph = source_textbox.text_frame.add_paragraph()
    paragraph.text = llm_insight
    paragraph.font.name = "Univers Next for HSBC Light"
    paragraph.font.size = Pt(13.8)
    source_textbox.text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    source_textbox.text_frame.vertical_anchor = MSO_VERTICAL_ANCHOR.MIDDLE
    source_textbox.text_frame.word_wrap = True
    source_textbox.text_frame.vertical_anchor = MSO_VERTICAL_ANCHOR.TOP
    source_textbox.text_frame.margin_left = 0
    source_textbox.text_frame.margin_top = 0
    source_textbox.text_frame.margin_bottom = 0

    #   End: Second Slide
    ##################################################################

    ##################################################################
    #   Save the ppt
    X.save(output_path)
    return
