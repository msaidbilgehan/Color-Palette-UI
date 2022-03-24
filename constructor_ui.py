
### ### ### ### ### ## ### ### ### ###
### ### ### BUILT-IN LIBRARIES ### ###
### ### ### ### ### ## ### ### ### ###
import logging
import cv2
import numpy as np

### ### ### ### ## ## ## ### ### ###
### ### ### CUSTOM LIBRARIES ### ###
### ### ### ### ## ## ## ### ### ###
import libs

from stdo import stdo
from qt_tools import qtimer_Create_And_Run, list_Widget_Item, lcdNumber_Set, get_Color
from tools import load_from_json, save_to_json, list_files
from image_manipulation import color_Range_Mask_2, erosion, dilation

from structure_ui import init_and_run_UI, Graphics_View  # , Structure_UI, init_UI
from structure_camera import CAMERA_FLAGS
from structure_ui_camera import Structure_Ui_Camera
from structure_threading import Thread_Object


### ### ### ### ### ## ## ## ### ### ### ### ###
### ### ### CAMERA UI CONFIGURATIONS ### ### ###
### ### ### ### ### ## ## ## ### ### ### ### ###

class Graphics_View_LCD(Graphics_View):
    def __init__(self, *args, **kwargs):
        super(Graphics_View_LCD, self).__init__(*args, **kwargs)
        
        self.is_Connected_LCDs = False
        self.lcdNumber_XY_list = list()
        self.lcdNumber_RGB_list = list()
        
        # self.red = 0
        # self.green = 0 
        # self.blue = 0
    
    def mouseMoveEvent(self, event):
        super(Graphics_View_LCD, self).mouseMoveEvent(event)
        # self.mouse_Events["mouseMove"] = True
        if self.is_Connected_LCDs:
            if self.lcdNumber_XY_list != []:
                lcdNumber_Set(
                    # mouseMove_position
                    self.lcdNumber_XY_list,
                    [
                        self.mouse_Events["mouseMove_position_scene"].x(),
                        self.mouse_Events["mouseMove_position_scene"].y()
                    ]
                )
            if self.lcdNumber_RGB_list != []:
                red, green, blue = self.color_Picker()
                lcdNumber_Set(
                    self.lcdNumber_RGB_list,
                    [
                        red,
                        green,
                        blue,
                        int((red + green + blue) / 3)
                        if red + green + blue != 0
                        else 0,
                        int(255 - (red + green + blue) / 3)
                        if red + green + blue != 0
                        else 0
                    ]
                )

    def mouseDoubleClickEvent(self, event):
        super(Graphics_View_LCD, self).mouseDoubleClickEvent(event)
        # self.red, self.green, self.blue = self.color_Picker()
        self.connector_mouseDoubleClickEvent(
            self.color_Picker()
        )

class Ui_Color_Palette(Structure_Ui_Camera):
    logger_level = logging.INFO
    #__Threads = dict()
    
    def __init__(self, *args, obj=None, logger_level=logging.INFO, **kwargs):
        super(Ui_Color_Palette, self).__init__(*args, **kwargs)

        ### ### ### ### ###
        ### Constractor ###
        ### ### ### ### ###
        self.logger_level = logger_level
        self.__thread_Dict = dict()
        self.buffer_graphicsView_Camera_Process_Color_Mask = None
        self.kernels = {
            str((3, 3)): (3, 3),
            str((5, 5)): (5, 5),
            str((7, 7)): (7, 7),
            str((10, 10)): (10, 10),
            str((3, 5)): (3, 5),
            str((5, 3)): (5, 3),
            str((3, 7)): (3, 7),
            str((7, 3)): (7, 3),
            str((10, 5)): (10, 5),
            str((5, 10)): (5, 10)
        }
        self.comboBox_Color_Mask_Kernel.addItems(
            [kernel for kernel in self.kernels.keys()]
        )
        self.graphicsView_Camera.lcdNumber_XY_list = [
            self.lcdNumber_Pointer_X,
            self.lcdNumber_Pointer_Y
        ]
        self.graphicsView_Camera.lcdNumber_RGB_list = [
            self.lcdNumber_Pointer_Color_Red,
            self.lcdNumber_Pointer_Color_Green,
            self.lcdNumber_Pointer_Color_Blue,
            self.lcdNumber_Pointer_Color_Grayscale,
            self.lcdNumber_Pointer_Color_Grayscale_Inverted
        ]
        self.graphicsView_Camera.is_Connected_LCDs = True
        self.graphicsView_Camera.connector_mouseDoubleClickEvent = self.color_Picker_Double_Click_Action

        ### ### ### ### ###
        ### ### Init ### ##
        ### ### ### ### ###
        self.init()
        
        ###
        self.process_Thread_Start(
            trigger_quit=self.is_Quit_App, 
            trigger_pause=self.checkBox_Process_Active.isChecked
        )

        self.loaded_color_palette = {
            "Lower_Red": self.spinBox_Color_Palette_Lower_Red.value(),
            "Upper_Red": self.spinBox_Color_Palette_Upper_Red.value(),
            "Lower_Green": self.spinBox_Color_Palette_Lower_Green.value(),
            "Upper_Green": self.spinBox_Color_Palette_Upper_Green.value(),
            "Lower_Blue": self.spinBox_Color_Palette_Lower_Blue.value(),
            "Upper_Blue": self.spinBox_Color_Palette_Upper_Blue.value(),
            "is_HSV": self.checkBox_is_HSV.isChecked(),
            "Color_Mask_Kernel": self.checkBox_Color_Mask_Kernel.isChecked(),
            "Color_Mask_Kernel_Min": self.spinBox_Color_Mask_Kernel_Min.value(),
            "Color_Mask_Kernel_Max": self.spinBox_Color_Mask_Kernel_Max.value()
        }
        self.color_palette_file_paths = list()
        self.load_Color_Palettes("./")
        
    ### ### ## ### ###
    ### OVERWRITES ###
    ### ### ## ### ###
    
    def init(self):

        self.configure_Other_Settings()
        self.connect_to_Camera(
            CAMERA_FLAGS.CV2,
            # self.spinBox_Buffer_Size.value(),
            0,
            10,
            self.exposure_Time
        )
        self.graphicsView_Camera.init_Render_QTimer(
            connector_stream=self.stream_Flow,
            delay = 0.0001
        )
        ### Initialize Graphics View Object Variables
        self.graphicsView_Camera_Process_Color_Mask.LCD_Number_List = [
            self.lcdNumber_Pointer_Color_Red,
            self.lcdNumber_Pointer_Color_Green,
            self.lcdNumber_Pointer_Color_Blue,
            self.lcdNumber_Pointer_Color_Grayscale,
            self.lcdNumber_Pointer_Color_Grayscale_Inverted
        ]
        
        self.camera_Instance.api_Set_Camera_Size(resolution=(1920, 1080))
        
    def init_QTimers(self, *args, **kwargs):
        super(Ui_Color_Palette, self).init_QTimers(*args, **kwargs)

    def configure_Button_Connections(self):
        self.pushButton_Set_Exposure.clicked.connect(
            lambda: self.set_Camera_Exposure(
                self.spinBox_Exposure_Time.value()
            )
        )
        self.pushButton_Load_Image.clicked.connect(
            lambda: [
                self.stream_Switch(False),
                self.graphicsView_Renderer(
                    self.graphicsView_Camera,
                    self.load_Image_Action(
                        path=self.QFileDialog_Event(
                            "getOpenFileName",
                            [
                                "Open file",
                                "",
                                "Image files (*.png *.jpg *.jpeg)"
                            ]
                        )[0]
                    )
                ),
            ]
        )
        self.pushButton_Save_Image.clicked.connect(
            lambda: self.save_Image_Action(
                # self.camera_Instance.stream_Returner(auto_pop=False),
                img=self.api_Get_Buffered_Image(),
                path=None,
                filename=[],
                format="png"
            )
        )
        self.pushButton_Connect_to_Camera.clicked.connect(
            lambda: self.connect_to_Camera(
                CAMERA_FLAGS.CV2,
                # self.spinBox_Buffer_Size.value(),
                10,
                self.exposure_Time
            )
        )
        self.pushButton_Remove_the_Camera.clicked.connect(
            self.camera_Remove
        )
        self.pushButton_Stream_Switch.clicked.connect(
            lambda: self.stream_Switch()
        )
        self.pushButton_Load_Video.clicked.connect(
            self.load_Video
        )
        self.pushButton_save_palette.clicked.connect(
            self.save_Palette
        )
        self.pushButton_load_palette.clicked.connect(
            self.load_Palette
        )
        self.pushButton_refresh_palettes.clicked.connect(
            lambda: self.load_Color_Palettes("./")
        )
        self.pushButton_Double_Click_Listener.clicked.connect(
            self.action_Double_Click_Listener
        )
        
    def load_Video(self):
        # self.camera_Remove()
        self.stream_Switch(False)
        # self.graphicsView_Renderer(
        #     self.graphicsView_Camera,
        #     self.load_Image_Action(
        #         path=self.QFileDialog_Event(
        #             "getOpenFileName",
        #             [
        #                 "Open file",
        #                 "",
        #                 "Image files (*.png *.jpg *.jpeg)"
        #             ]
        #         )[0]
        #     )
        # )
        
        
        self.QTimer_Dict["video_Process"] = qtimer_Create_And_Run(
            self,
            lambda: self.video_Process(
                self.QFileDialog_Event(
                    "getOpenFileName",
                    [
                        "Open file",
                        "",
                        "Image files (*.mp4 *.avi)"
                    ]
                )[0]
            ),
            500,
            is_needed_start=True, 
            is_single_shot=True
        )
    
    def video_Process(self, path):
        if path is not None:
            # self.checkBox_Process_Active.setChecked(False)
            
            # self.graphicsView_Camera.init_Render_QTimer(
            #     connector_stream=self.stream_Flow,
            #     delay=0.0001
            # )
            self.graphicsView_Camera.stop_Render_QTimer()
            video_object = cv2.VideoCapture(path)
            # self.graphicsView_Camera_Process_Color_Mask.init_Render_QTimer(
            #     connector_stream=lambda: self.buffer_graphicsView_Camera_Process_Color_Mask,
            #     delay=1
            # )
            is_successfull = True
            while is_successfull:
                is_successfull, video_frame = video_object.read()
                if is_successfull:
                    self.camera_Buffer = video_frame
            video_object.release()

    def configure_Other_Settings(self):
        self.checkBox_Process_Active.stateChanged.connect(
            self.action_checkbox_Process
        )
        # self.action_About_Page.triggered.connect(
        #     self.about_Page(self)
        # )

        # self.color_palette = load_from_json(
        #     "color_palette.json"
        # )

    def closeEvent(self, *args, **kwargs):
        super(Ui_Color_Palette, self).closeEvent(*args, **kwargs)
        
        self.camera_Remove()

    ### ### ## ### ###
    ### ### ## ### ###
    ### ### ## ### ###

    def save_Palette(self):
        path = self.lineEdit_color_palette_name.text() if \
            self.lineEdit_color_palette_name.text() else "default_color_palette.json"
        self.loaded_color_palette = {
            "Lower_Red": self.spinBox_Color_Palette_Lower_Red.value(),
            "Upper_Red": self.spinBox_Color_Palette_Upper_Red.value(),
            "Lower_Green": self.spinBox_Color_Palette_Lower_Green.value(),
            "Upper_Green": self.spinBox_Color_Palette_Upper_Green.value(),
            "Lower_Blue": self.spinBox_Color_Palette_Lower_Blue.value(),
            "Upper_Blue": self.spinBox_Color_Palette_Upper_Blue.value(),
            "is_HSV": self.checkBox_is_HSV.isChecked(),
            "Color_Mask_Kernel": self.checkBox_Color_Mask_Kernel.isChecked(),
            "Color_Mask_Kernel_Min": self.spinBox_Color_Mask_Kernel_Min.value(),
            "Color_Mask_Kernel_Max": self.spinBox_Color_Mask_Kernel_Max.value()
        }
        save_to_json(
            path,
            self.loaded_color_palette
        )
        self.load_Color_Palettes("./")
        
    def load_Palette(self):
        # path = self.lineEdit_color_palette_name.text() if \
        #     self.lineEdit_color_palette_name.text() else "default_color_palette.json"
        
        if self.listWidget_color_palettes.currentRow() > -1:
            self.loaded_color_palette = load_from_json(
                self.color_palette_file_paths[
                    self.listWidget_color_palettes.currentRow()
                ]
            )

            if self.loaded_color_palette is not None:
                self.lineEdit_color_palette_name.setText(
                    self.color_palette_file_paths[
                        self.listWidget_color_palettes.currentRow()
                    ].split("/")[-1]
                )
                # Red
                self.spinBox_Color_Palette_Lower_Red.setValue(
                    self.loaded_color_palette["Lower_Red"]
                )
                self.spinBox_Color_Palette_Upper_Red.setValue(
                    self.loaded_color_palette["Upper_Red"]
                )

                # Green
                self.spinBox_Color_Palette_Lower_Green.setValue(
                    self.loaded_color_palette["Lower_Green"]
                )
                self.spinBox_Color_Palette_Upper_Green.setValue(
                    self.loaded_color_palette["Upper_Green"]
                )
                
                # Blue
                self.spinBox_Color_Palette_Lower_Blue.setValue(
                    self.loaded_color_palette["Lower_Blue"]
                )
                self.spinBox_Color_Palette_Upper_Blue.setValue(
                    self.loaded_color_palette["Upper_Blue"]
                )
                
                # HSV
                self.checkBox_is_HSV.setChecked(
                    self.loaded_color_palette["is_HSV"]
                )
                
                # Kernel
                self.checkBox_Color_Mask_Kernel.setChecked(
                    self.loaded_color_palette["Color_Mask_Kernel"]
                )
                self.spinBox_Color_Mask_Kernel_Min.setValue(
                    self.loaded_color_palette["Color_Mask_Kernel_Min"]
                )
                self.spinBox_Color_Mask_Kernel_Max.setValue(
                    self.loaded_color_palette["Color_Mask_Kernel_Max"]
                )
    
    def load_Color_Palettes(self, path):
        self.color_palette_file_paths = list_files(
            path=path,
            extensions=[".json"],
            recursive=False
        )
        self.listWidget_color_palettes.clear()
        for color_palette_path in self.color_palette_file_paths:
            self.qt_Priority()
            self.listWidget_color_palettes.addItem(
                list_Widget_Item(
                    title=color_palette_path.split("/")[-1]
                )
            )

    ### ### ## ### ###
    ### ### ## ### ###
    ### ### ## ### ###
    
    def action_Double_Click_Listener(self):
        self.QTimer_Dict["action_Double_Click_Listener"] = qtimer_Create_And_Run(
            self,
            self.color_Picker_Double_Click_Listener,
            100,
            is_single_shot=True
        )
    
    def color_Picker_Double_Click_Listener(self):
        self.graphicsView_Camera.mouse_Events["mouseDoubleClick"] = False
        while not self.graphicsView_Camera.mouse_Events["mouseDoubleClick"]:
            self.qt_Priority()
        # self.graphicsView_Camera.mouse_Events["mouseDoubleClick_position_scene"]
        # (self.red, self.green, self.blue)

        red, green, blue = self.graphicsView_Camera.color_Picker()
        self.spinBox_Color_Palette_Double_Click_Red.setValue(red)
        self.spinBox_Color_Palette_Double_Click_Green.setValue(green)
        self.spinBox_Color_Palette_Double_Click_Blue.setValue(blue)
    
    def color_Picker_Double_Click_Action(self, params):
        red, green, blue = params
        self.spinBox_Color_Palette_Double_Click_Red.setValue(red)
        self.spinBox_Color_Palette_Double_Click_Green.setValue(green)
        self.spinBox_Color_Palette_Double_Click_Blue.setValue(blue)
    
    def stream_Flow(self):
        return self.camera_Instance.stream_Returner() \
            if self.camera_Instance is not None else None

    '''
    This code is a thread that runs the deep face process The code will run in a loop 
    until it receives quit signal from main program When the code gets pause signal 
    it will wait for resume signal before continue running
    - generated by stenography autopilot [ 🚗👩‍✈️ ]
    '''
    def process_Thread_Start(self, trigger_quit=None, trigger_pause=None):
        self.__thread_Dict["process_Thread"] = Thread_Object(
            name="Constructor.process_Thread",
            delay=0.1,
            # logger_level=None,
            set_Deamon=True,
            run_number=None,
            quit_trigger=trigger_quit
        )
        self.__thread_Dict["process_Thread"].init(
            params=[],
            task=self.process
        )
        self.__thread_Dict["process_Thread"].start()
        
    def action_checkbox_Process(self):
        if self.checkBox_Process_Active.isChecked():
            self.graphicsView_Camera_Process_Color_Mask.init_Render_QTimer(
                connector_stream=lambda: self.buffer_graphicsView_Camera_Process_Color_Mask,
                delay=1
            )
        else:
            self.graphicsView_Camera_Process_Color_Mask.stop_Render_QTimer()

    def process(self):
        image = None
        if self.checkBox_Process_Active.isChecked():
            image = self.stream_Flow()
            
            if image is not None:
                is_color_Range_Mask, max_matched_frame_coords, mask = color_Range_Mask_2(
                    img=image,
                    color_palette_lower=(
                        self.spinBox_Color_Palette_Lower_Blue.value(),
                        self.spinBox_Color_Palette_Lower_Green.value(),
                        self.spinBox_Color_Palette_Lower_Red.value()
                    ),
                    color_palette_upper=(
                        self.spinBox_Color_Palette_Upper_Blue.value(),
                        self.spinBox_Color_Palette_Upper_Green.value(),
                        self.spinBox_Color_Palette_Upper_Red.value()
                    ),
                    is_HSV=self.checkBox_is_HSV.isChecked(),
                )
                # is_color_Range_Mask, max_matched_frame_coords, mask = color_Range_Mask(
                #     img=image,
                #     color_palette=self.color_palette,
                #     type_color=self.comboBox_Color_Mask_Type.currentText(),
                #     ranged_color=self.comboBox_Color_Mask_Range.currentText().lower()
                # )
                if is_color_Range_Mask:
                    if self.checkBox_Color_Mask_Kernel.isChecked():
                        if self.comboBox_Color_Mask_Kernel.currentText().lower() == "custom":
                            kernel = np.ones((
                                self.spinBox_Color_Mask_Kernel_Min.value(),
                                self.spinBox_Color_Mask_Kernel_Max.value()
                            ), np.uint8)
                        else:
                            kernel = np.ones(
                                self.kernels[self.comboBox_Color_Mask_Kernel.currentText()], 
                                np.uint8
                            )
                        self.qt_Priority()
                        mask = erosion(mask, kernel)
                        mask = dilation(mask, kernel)
                    # image = image[
                    #     max_matched_frame_coords[1]: max_matched_frame_coords[1] + max_matched_frame_coords[3],
                    #     max_matched_frame_coords[0]: max_matched_frame_coords[0] + max_matched_frame_coords[2],
                    # ]
                    masked_image = image.copy() 
                    masked_image[mask != 255] = 0
                    self.buffer_graphicsView_Camera_Process_Color_Mask = masked_image
                    image = masked_image
        return image

        
### ### ### ### ### ## ## ## ### ### ### ### ###
### ### ### ### ### ## ## ## ### ### ### ### ###
### ### ### ### ### ## ## ## ### ### ### ### ###

if __name__ == "__main__":
    # title, Class_UI, run=True, UI_File_Path= "test.ui", qss_File_Path = ""
    stdo(1, "Running {}...".format(__name__))
    app, ui = init_and_run_UI(
        "Process Test",
        Ui_Color_Palette,
        UI_File_Path="color_Palette_UI.ui"
    )
