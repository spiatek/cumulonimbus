
import os.path

import urllib

import swift.common.client as scc

import dir
import file

class NoSuchFileOrDirectory( Exception ) : pass
# in default swift doesnt alarm if container exists do we need this?
#class DirectoryExists( Exception ) : pass

def sw2fs( path ) :
	return urllib.unquote_plus( path )

def fs2sw( path ) :
	return urllib.quote_plus( path )

class Dir( dir.Dir ) :
	def __init__( self , connection , mode ) :
		dir.Dir.__init__( self , mode ) 

		self.con = connection

class File( file.File ) :
	pass

class Swift :
	con = None

	def __init__( self , authurl , user , key ) :
		''' Connect to swift server and create root directory '''
		self.con = scc.Connection( authurl , user , key )
		self.dirs = {}
#        try :
		self.mkdir('/')
#        except DirectoryExists :
#            pass

	def _flush( self ) :
		''' force send all data to swift server '''
		pass

	def _synced( self , file ) :
		return False

	def _sync_dirs( self ) :
		if self._synced( 'dirs.timestamp' ) :
			return

		self.dirs = {}
		for p in self.con.get_account()[1] :
			name = sw2fs(p['name'])
			self.dirs[name] = Dir( self.con , 0644 )

		for path , dir in self.dirs.items() :
			parent_path , name = os.path.split(path)
			parent = self.dirs[parent_path]
			if name != '' :
				parent.set_child( name , dir )
				dir.set_parent( parent )

	def sync( self ) :
		''' synchronize with swift server '''
		pass

	def get( self , path ) :
		''' recive file or dir given by path '''
		assert( self.con != None ) 

		path = os.path.normpath(path)

		cont , obj = os.path.split(path)

		try :
			# check if such dir exist
			self.con.get_container(fs2sw(path))
			self._sync_dirs()
			return self.dirs[path]
		except scc.ClientException as e :
			if e.http_status != 404 : raise e
			cont , obj = os.path.split(path)
			if obj == '' : raise NoSuchFileOrDirectory(path)

			try :
				obj = self.con.get_object(fs2sw(cont),obj)
			except scc.ClientException as e :
				if e.http_status == 404 :
					raise NoSuchFileOrDirectory(path)
				else : raise e
			return File(0600,obj[1])
		assert(False)

	def put( self , path , file ) :
		'''
		send file at given path 

		can rise error if path is invalid
		'''
		assert( self.con != None )

		cont , obj = os.path.split(path)

		if obj == '' :
			raise ValueError('cannot put file with empty name')

		self.get(cont)

		try :
			self.con.put_object(fs2sw(cont),obj,file.contents())
		except scc.ClientException as e :
			if e.http_status == 404 :
				raise NoSuchFileOrDirectory(cont)
			else : raise e

	def mkdir( self , path  , parents = False ) :
		'''
		creates new directory on swift server

		can rise error if path is invalid

		if parents is true, parents are created
		if they dont exists
		'''
		assert( self.con != None )

		swpath = fs2sw(path)

		if path == '/' : # FIXME: is this portable?
			self.con.put_container(swpath)
			return

		path = os.path.normpath(path)

		if not parents :
			parent , obj = os.path.split(path)
			swpar = fs2sw(parent)
			for p in self.con.get_account()[1] :
				if p['name'] == swpar :
					self.con.put_container(fs2sw(path))
					return
			raise NoSuchFileOrDirectory(parent)
		else :
			directory = path
			while directory != '/' : # FIXME: is this portable?
				self.con.put_container(fs2sw(directory))
				directory = os.path.split(directory)[0]

	def rm( self , path , recursive = False , force = False ) :
		''' removes file or directory '''
		assert( self.con != None )

		path = os.path.normpath(path)

		if recursive : 
			try :
				self._rm_dir( path )
			except scc.ClientException as e :
				if e.http_status != 404 : raise e
				self._rm_file( path )
		else :
			self._rm_file( path )

	def _rm_dir( self , path ) :
		swpath = fs2sw(path)

		# check if path is a dir
		self.con.get_container( swpath )

		# delete subdirectries
		for p in self.con.get_account()[1] :
			name = p['name']
			if name[:len(swpath)] == swpath : # p is substring
				for p in self.con.get_container(name)[1] :
					self.con.delete_object(name,p['name'])
				self.con.delete_container(name)

	def _rm_file( self , path ) :
		cont , obj = os.path.split(path)
		if obj == '' : raise NoSuchFileOrDirectory(path)

		try :
			self.con.delete_object(fs2sw(cont),obj)
		except scc.ClientException as e :
			if e.http_status == 404 :
				raise NoSuchFileOrDirectory(path)
			else : raise e

