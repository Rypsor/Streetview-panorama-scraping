import asyncio
import json
import os
import traceback
import glob
import aiohttp

import streetview

BASE_PATH = "/media/samuel/SSD/medellin_panoramas/input_panoramas"  # O "E:\\MiDisco" en Windows
PATH_TILES = os.path.join(BASE_PATH, "tiles")
PATH_PANORAMAS = os.path.join(BASE_PATH, "panoramas")

async def download_tiles_async(tiles, directory, session):
    """ Downloads all the tiles in a Google Stree View panorama into a directory. """
    total_tiles = len(tiles)
    for i, (x, y, fname, url) in enumerate(tiles):
        # Try to download the image file
        url = url.replace("http://", "https://")
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(directory + '/' + fname, 'wb') as out_file:
                            out_file.write(content)
                        print(f"\rDownloading tile {i+1}/{total_tiles}", end="", flush=True)
                        break
                    else:
                        print(f"\nFailed to download tile {fname}: HTTP {response.status}")
                        retry_count += 1
            except Exception as e:
                print(f"\nError downloading tile {fname}: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    print(f"Retrying... ({retry_count}/{max_retries})")
                    await asyncio.sleep(1)  # Wait a second before retrying
        
        if retry_count >= max_retries:
            print(f"\nFailed to download tile {fname} after {max_retries} attempts")


async def download_panorama(panoid,
                            session=None,
                            tile_diretory= PATH_TILES,
                            pano_directory= PATH_PANORAMAS):
    """ 
    Downloads a panorama from latitude and longitude
    Heavily IO bound (~98%), ~40s per panorama without using asyncio.
    """
    if not os.path.isdir(tile_diretory):
        os.makedirs(tile_diretory)
    if not os.path.isdir(pano_directory):
        os.makedirs(pano_directory)

    try:
        x = streetview.tiles_info(panoid['panoid'])
        await download_tiles_async(x, tile_diretory, session)
        
        # Check if all tiles were downloaded successfully
        all_tiles_exist = all(os.path.exists(os.path.join(tile_diretory, fname)) 
                            for _, _, fname, _ in x)
        
        if all_tiles_exist:
            try:
                streetview.stich_tiles(panoid['panoid'],
                                    x,
                                    tile_diretory,
                                    pano_directory,
                                    point=(panoid['lat'], panoid['lon']))
            except KeyboardInterrupt:
                print("\nInterrupted during image stitching. Cleaning up...")
                # Clean up partial files
                partial_file = f"{panoid['lat']}_{panoid['lon']}_{panoid['panoid']}.jpg"
                partial_path = os.path.join(pano_directory, partial_file)
                if os.path.exists(partial_path):
                    os.remove(partial_path)
                raise
            except Exception as e:
                print(f"Error during image stitching: {str(e)}")
                raise
        else:
            print(f"Some tiles are missing for panorama {panoid['panoid']}")
            raise Exception("Incomplete tile download")
            
        # Only delete tiles if everything was successful
        streetview.delete_tiles(x, tile_diretory)

    except KeyboardInterrupt:
        print(f"\nInterrupted while processing panorama {panoid['panoid']}. Cleaning up...")
        raise
    except Exception as e:
        print(f'Failed to create panorama: {str(e)}\n{traceback.format_exc()}')


def panoid_created(panoid):
    """ Checks if the panorama was already created """
    file = f"{panoid['lat']}_{panoid['lon']}_{panoid['panoid']}.jpg"
    return os.path.isfile(os.path.join(PATH_PANORAMAS, file))


async def download_loop(panoids, pmax):
    """ Main download loop """
    conn = aiohttp.TCPConnector(limit=10)  # Reduced connection limit for stability
    async with aiohttp.ClientSession(connector=conn,
                                     auto_decompress=False) as session:
        try:
            # Filter panoramas that haven't been created yet
            pending_panoids = [p for p in panoids[:pmax] if not panoid_created(p)]
            total = len(pending_panoids)
            
            if total == 0:
                print("No new panoramas to download in this batch")
                return
                
            print(f"\nProcessing {total} panoramas in this batch")
            
            # Process panoramas one by one for better progress tracking
            for i, panoid in enumerate(pending_panoids, 1):
                try:
                    print(f"\nDownloading panorama {i}/{total} (ID: {panoid['panoid']})")
                    await download_panorama(panoid, session=session)
                except Exception as e:
                    print(f"Error processing panorama {panoid['panoid']}: {str(e)}")
                    continue
        except Exception as e:
            print(f"Error in download loop: {str(e)}")
            print(traceback.format_exc())


async def main():
    # Load panoids info
    if not glob.glob('panoids*.json'):
        print('No panoids file found')
        exit()
    elif len(glob.glob('panoids*.json')) > 1:
        print('Multiple panoids files found. Please remove files not needed')
        exit()

    with open(glob.glob('panoids*.json')[0], 'r') as f:
        panoids = json.load(f)

    print(f"Loaded {len(panoids)} panoids")

    # Download panorama in batches of 100
    i = 0
    try:
        while True:
            i += 1
            print(f'Running the next batch: {(i-1)*100+1} → {i*100}')
            await download_loop(panoids, 100 * i)
            if 100 * i > len(panoids):
                break
    except KeyboardInterrupt:
        print("\nDownload interrupted by user. Cleaning up...")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
