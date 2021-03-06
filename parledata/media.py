# -*-coding:utf-8 -*-
"""
PlwMedia

"""


# IMPORT
import sys
import os
import datetime
import logging

from jinja2 import Environment, PackageLoader, select_autoescape, FileSystemLoader, TemplateNotFound, TemplateSyntaxError, UndefinedError
import markdown2
import json
import csv
from PIL import Image
from PIL.ExifTags import TAGS

import shutil
import re
from .misc import strip_accents
from .log import logger


#
# Convert Media files
#
class PlwMedia(object):
    def __init__(self):

        self.resize = [ [300, 1, 1],
                        [700, 1.5, 1.5],
                        [2000, 2.5, 8] ]
        self.resizelen = len(self.resize);
        for i in self.resize:
            logger.info('img %d, resize %f, thum %f' %(i[0], i[1], i[2]))

    def __del__(self):
        pass

    def copyfile(self, foldername, sourcedir, targetdir, scanfor = '.jpg', scanoption = '@all', jsonfile = "copyfile.json"):
        if( targetdir[-1] != '\\' ):
            targetdir += "\\"
        logger.info("COPYFILE source %s to %s for %s (option %s)" %(sourcedir, targetdir, scanfor, scanoption))

        isOk = True
        isScanOnlyfiles = scanoption.lower().find('@files')
        logger.info("isScanOnlyfiles "+str(isScanOnlyfiles))
        imagelist = {}
        try:
            for dirnum, (dirpath, dirs, files) in enumerate(os.walk(sourcedir)):
                nbFiles = 0
                for filename in files:
                    filenamenoext = filename.split(".")[0].lower()
                    filename = filename.lower()
                    fname = os.path.join(dirpath,filename).lower()
                    if fname.endswith(scanfor):
                        nbFiles += 1

                        if( isScanOnlyfiles == -1 ):
                            subdir = dirpath[len(sourcedir):]
                            if subdir[-1] != '\\':
                                subdir += '\\'
                            newfile = targetdir+subdir+filename
                            logger.debug("dir "+dirpath + " subdir "+subdir+" file "+filename)
                        else:
                            newfile = targetdir+filename


                        try:
                            logger.debug('copy %s in %s' %(fname, newfile))
                            shutil.copy(fname, newfile)
                        except FileNotFoundError:
                            getdir = os.path.dirname(newfile)
                            logger.info("create directory "+getdir+" from "+newfile)
                            try:
                                os.makedirs(getdir, 0o777)
                                shutil.copy(fname, newfile)
                            except:
                                raise

                if( nbFiles > 0 ):
                    logger.info("find in directory %s : %d files like %s" %(dirpath, nbFiles, scanfor))
                if isScanOnlyfiles >= 0:
                    imagelist['folder'] = foldername
                    imagelist['nbfiles'] = nbFiles
                    break

        except ValueError as e:
                logger.critical("Error copyfile "+cstr(e))
                isOk = False

        newjson = targetdir+jsonfile
        isOk = self.jsondir(newjson, imagelist)

        return isOk



    # scanimage
    #    copy image to static path
    #    resize
    #    option: @files for only source directory (no subdirs)
    def scanimage(self, foldername, sourcedir, targetdir, resizeimg = 2.5, resizeimgth = 10, scanfor = '.jpg', scanoption = '@files', jsonfile = "scanimage.json"):
        resize = [ [0, resizeimg, resizeimgth] ]
        resizelen = len(resize)
        self.scanmedia(foldername, sourcedir, targetdir, resize, resizelen, scanfor, scanoption, jsonfile)

    def isextensiontype(self, fname, scanfor):
        ext = scanfor.lower().split('|')
        for i in ext:
            if fname.endswith(i):
                return i;
        return None;

    def scanmedia(self, foldername, sourcedir, targetdir, resize = [], resizelen = 0, scanfor = '.jpg', scanoption = '@files', jsonfile = "scanimage.json"):
        if( resizelen == 0 ):
            resize = self.resize
            resizelen = self.resizelen

        if( targetdir[-1] != '\\' ):
            targetdir += "\\"
        logger.info("SCANIMAGE source %s to %s for %s (option %s)" %(sourcedir, targetdir, scanfor, scanoption))
        nbFiles = 0
        nbFilesAll = 0
        isOk = True
        isScanOnlyfiles = scanoption.lower().find('@files')
        logger.info("isScanOnlyfiles "+str(isScanOnlyfiles))
        dashboard = { 'nbfiles': 0, 'nbfolder' : 0, 'folder' : {} }
        imagelist = {}
        resizeimg = 0
        resizeimgth = 0
        nbFolder = 0
        subdir = None
        try:
            for dirnum, (dirpath, dirs, files) in enumerate(os.walk(sourcedir)):
                nbFiles = 0
                sizeFileW = 0
                sizeFileH = 0
                for filename in files:
                    filenamenoext = filename.split(".")[0].lower()
                    filename = filename.lower()
                    fname = os.path.join(dirpath,filename).lower()
                    ext = self.isextensiontype(fname, scanfor)
                    if ext:
                    #if fname.endswith(scanfor):
                        nbFiles += 1
                        if( ext in dashboard ):
                            dashboard[ext] += 1
                        else:
                            dashboard[ext] = 1



                        img = Image.open(fname)
                        nx, ny = img.size
                        logger.info("====> image %s format %s width %s mode %s" %(filename, img.format, str(img.size), img.mode))
                        for i in resize:
                            if( i[0] <= nx ):
                                resizeimg = i[1]
                                resizeimgth = i[2]
                        logger.info('resize with %f and %f' %(resizeimg, resizeimgth))

                        exif270_imagedescription = None
                        exif306_datetime = None

                        try:
                            # EXIF DOCUMENTATION
                            # http://www.exiv2.org/tags.html

                            exif = img._getexif()
                            if( 270 in exif ):
                                #logger.info(exif)
                                #logger.info('EXIF 270 '+exif[270])
                                exif270_imagedescription = exif[270]
                            if( 306 in exif ):
                                #logger.info('EXIF 306 '+exif[306])
                                exif306_datetime = exif[306]
                        except:
                            pass


                        if( isScanOnlyfiles == -1 ):
                            #import pdb; pdb.set_trace()
                            subdir = dirpath[len(sourcedir):]
                            if( len(subdir) > 0 ):
                                if subdir[-1] != '\\':
                                    subdir += '\\'
                            newfile = targetdir+subdir+filename
                            newfileth = targetdir+subdir+"th-"+filename
                            logger.debug("dir "+dirpath + " subdir "+subdir+" file "+filename)
                        else:
                            newfile = targetdir+filename
                            newfileth = targetdir+"th-"+filename


                        # replace strings for urls
                        newfile = strip_accents(re.sub(r"[^\w\\\\:.]", '-', newfile))
                        newfileth = strip_accents(re.sub(r"[^\w\\\\:.]", '-', newfileth))


                        imgresize = img.resize((int(nx/resizeimg), int(ny/resizeimg)), Image.BICUBIC)
                        try:
                            imgresize.save(newfile,dpi=(100,100))
                        except FileNotFoundError:
                            getdir = os.path.dirname(newfile)
                            logger.info("create directory "+getdir+" from "+newfile)
                            try:
                                os.makedirs(getdir, 0o777)
                                imgresize.save(newfile,dpi=(100,100))
                            except:
                                raise

                        imgresizeth = img.resize((int(nx/resizeimgth), int(ny/resizeimgth)), Image.BICUBIC)
                        imgresizeth.save(newfileth,dpi=(72,72))

                        imagelist[filenamenoext] = {
                            'folder' : subdir,
                            'src' : subdir+filename, 'srcw' : imgresize.width, 'srch' : imgresize.height,
                            'th' : subdir+'th-'+filename, 'thw' : imgresizeth.width, 'thh' : imgresizeth.height }
                        if( exif270_imagedescription ):
                            imagelist[filenamenoext]['exif270_imagedescription'] = exif270_imagedescription
                        if( exif306_datetime ):
                            imagelist[filenamenoext]['exif306_datetime'] = exif306_datetime
                        logger.info("resize %s in %s and %s" %(filename, str(imgresize.size), str(imgresizeth.size)))
                        sizeFileW += imgresize.size[0]
                        sizeFileH += imgresize.size[1]

                logger.info("find in directory %s : %d files like %s" %(dirpath, nbFiles, scanfor))
                if isScanOnlyfiles >= 0:
                    imagelist['folder'] = foldername
                    imagelist['nbfiles'] = nbFiles
                    imagelist['sizew'] = sizeFileW
                    imagelist['sizeh'] = sizeFileH
                    break
                else:
                    if( nbFiles > 0 and subdir ):
                        dashboard['folder'][subdir] = [ nbFiles, sizeFileW, sizeFileH ]
                        nbFolder += 1
                        nbFilesAll += nbFiles

        except ValueError as e:
                logger.critical("Error scanimage "+cstr(e))
                isOk = False
        dashboard['nbfiles'] = nbFilesAll
        dashboard['nbfolder'] = nbFolder
        imagelist['dashboard'] = dashboard

        newjson = jsonfile
        isOk = self.jsondir(newjson, imagelist)

        return isOk

    def jsondir(self, fout, data):
        logger.debug("JSON DUMP FROM SCANIMAGE")
        logger.debug(data)
        try:
            myFile = open(fout, "w", encoding='utf-8')
        except FileNotFoundError as e:
            getdir = os.path.dirname(fout)
            logger.info("create directory "+getdir+" from "+fout)
            try:
                os.makedirs(getdir, 0o777)
                try:
                    myFile = open(fout, "w", encoding='utf-8')
                except FileNotFoundError as e:
                    logger.critical("impossible to use file "+fout)
                    return False
            except:
                raise
        try:
            json.dump(data, myFile, indent=4)
        except ValueError as e:
            logger.critical("ERROR in json generation "+str(e))
        myFile.close()
        myFileinfo = os.stat(fout)
        logger.info("generate json file %s : %d bytes" % (fout, myFileinfo.st_size))
        logger.debug(data)
        return True



#
#
