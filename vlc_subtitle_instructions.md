# VLC Subtitle Formatting Instructions

VLC Player allows you to customize subtitle appearance through its settings. Follow these steps to achieve the desired subtitle formatting:

## Step 1: Configure VLC Subtitle Settings

1. Open VLC Player
2. Go to **Tools** > **Preferences** (or press **Ctrl+P**)
3. In the bottom left corner, select **All** under "Show settings" to show advanced options
4. Navigate to **Subtitles / OSD** in the left sidebar
5. Configure the following settings:

   - **Text size**: Set to a smaller value (e.g., 16-24) for compact font size
   - **Text color**: Set to white (#FFFFFF)
   - **Background opacity**: Set to around 128-180 for a dark grey background
   - **Outline thickness**: Set to 2-4 for better readability
   - **Outline color**: Set to black (#000000)
   - **Background color**: Set to dark grey (#333333)
   - **Alignment**: Set to "Center" for center alignment

6. Click **Save** to apply the changes

## Step 2: Configure Subtitle Position for Specific Videos

For videos where you want to position subtitles at the top (like for cue4 in SampleVideo):

1. While playing the video in VLC, right-click on the video
2. Select **Subtitles** > **Subtitle Track** > **Configure**
3. Adjust the **Vertical position** slider to move subtitles up or down
   - Move it toward the top (negative values) to position subtitles at the top of the screen
   - This setting can be adjusted in real-time while watching

## Step 3: Limit Lines Per Subtitle

VLC doesn't have a built-in setting to limit the number of lines per subtitle, but you can:

1. Use the modified SRT file we created (`SampleVideo_media_player_enhanced.srt`)
2. The conversion script already limits long subtitles to two lines

## Additional Tips

- **Keyboard shortcut**: Press **V** repeatedly while playing to cycle through subtitle visibility options
- **Subtitle delay**: Press **H** (delay subtitles) or **J** (speed up subtitles) to adjust timing if needed
- **Font selection**: You can also change the font in the Subtitles/OSD settings for better readability

These settings will be saved and applied to all videos you play in VLC. If you want different settings for different videos, you can create multiple VLC shortcuts with different configuration files.
