"""Small native controller for the offline Windows application."""
import bootstrap
import sys,threading,webbrowser,traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk,messagebox
import server

def main():
    if sys.platform=='win32':
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:pass
    root=tk.Tk();root.title('Pharma Stability 3.0');root.geometry('560x260');root.resizable(False,False)
    appserver=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
    server.PORT=appserver.server_address[1]
    url=f'http://127.0.0.1:{server.PORT}/'
    thread=threading.Thread(target=appserver.serve_forever,daemon=True);thread.start()
    ttk.Label(root,text='Pharma Stability 3.0',font=('Segoe UI',20,'bold')).pack(pady=(22,12))
    ttk.Label(root,text='Stability Program · Q1D · Q1E · Arrhenius\nChạy tại máy, không cần Internet để tính toán.\nGiữ cửa sổ này mở trong khi sử dụng.',font=('Segoe UI',11),justify='center').pack(pady=8)
    ttk.Button(root,text='Mở phần mềm',command=lambda:webbrowser.open(url)).pack(pady=8)
    ttk.Label(root,text=url,font=('Segoe UI',10)).pack()
    def stop():
        if messagebox.askokcancel('Đóng phần mềm','Lưu thiết kế và dự án chưa lưu trước khi đóng. Dừng phần mềm?',parent=root):
            if thread.is_alive():appserver.shutdown()
            appserver.server_close();root.destroy()
    root.protocol('WM_DELETE_WINDOW',stop)
    def poll():
        if thread.is_alive():root.after(1000,poll)
        else:appserver.server_close();root.destroy()
    root.after(700,lambda:webbrowser.open(url));root.after(1000,poll);root.mainloop()

if __name__=='__main__':
    try:main()
    except Exception:
        path=Path(__file__).parent/'startup-error.log';path.write_text(traceback.format_exc(),encoding='utf-8')
        messagebox.showerror('Không mở được StabilityLab',f'Chi tiết lỗi lưu tại {path}.')
